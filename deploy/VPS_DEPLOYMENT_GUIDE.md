# Image Gen MCP Server - VPS Deployment Guide

本指南详细说明如何在VPS服务器上使用Docker部署Image Gen MCP Server。

## 🚀 快速部署

### 前置要求

- Ubuntu 22.04 LTS VPS
- 2GB+ RAM, 2+ vCPU, 40GB+ SSD
- Root或sudo访问权限
- 域名（推荐，用于SSL）

### 一键部署

```bash
# 1. 下载部署脚本
wget https://raw.githubusercontent.com/your-repo/image-gen-mcp/main/deploy/vps-setup.sh

# 2. 运行部署脚本
chmod +x vps-setup.sh
./vps-setup.sh

# 3. 重启系统
sudo reboot
```

## 📋 手动部署步骤

### 1. 系统初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git vim htop tree
```

### 2. 安装Docker

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将当前用户添加到docker组
sudo usermod -aG docker $USER
newgrp docker
```

### 3. 创建应用目录

```bash
# 创建应用目录
sudo mkdir -p /opt/image-gen-mcp
sudo chown $USER:$USER /opt/image-gen-mcp
cd /opt/image-gen-mcp

# 创建必要的子目录
mkdir -p storage/{images,cache} logs monitoring nginx ssl
```

### 4. 上传应用代码

```bash
# 方法1: Git克隆
git clone <your-repo> .

# 方法2: SCP上传
scp -r ./image-gen-mcp user@your-server:/opt/image-gen-mcp/

# 方法3: rsync同步
rsync -avz --delete ./image-gen-mcp/ user@your-server:/opt/image-gen-mcp/
```

### 5. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

必须配置的环境变量：
```bash
# =============================================================================
# Provider Configuration
# =============================================================================
# OpenAI Provider (required for gpt-image-1, dall-e-3, dall-e-2)
PROVIDERS__OPENAI__API_KEY=sk-your-actual-openai-api-key-here
PROVIDERS__OPENAI__ENABLED=true

# Gemini Provider (optional for native Gemini image models)
PROVIDERS__GEMINI__API_KEY=your-actual-gemini-api-key-here
PROVIDERS__GEMINI__ENABLED=true

# =============================================================================
# Server Configuration
# =============================================================================
SERVER__NAME="Image Gen MCP Server"
SERVER__HOST=0.0.0.0
SERVER__PORT=3001

# =============================================================================
# Monitoring Configuration
# =============================================================================
GRAFANA_PASSWORD=your-secure-grafana-password
```

推荐的完整配置：
```bash
# 复制完整配置示例
cp .env.example .env

# 编辑配置文件
nano .env
```

配置说明：
- `PROVIDERS__OPENAI__API_KEY`: OpenAI API密钥（必需）
- `PROVIDERS__GEMINI__API_KEY`: Gemini API密钥（可选）
- `PROVIDERS__*__ENABLED`: 启用/禁用特定提供商
- `GRAFANA_PASSWORD`: Grafana监控面板密码
- `SERVER__HOST=0.0.0.0`: 允许外部访问（生产环境必需）

### 6. 安装和配置Nginx

```bash
# 安装Nginx
sudo apt install -y nginx

# 创建站点配置
sudo nano /etc/nginx/sites-available/image-gen-mcp
```

Nginx配置内容（替换your-domain.com）：
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;

server {
    listen 80;
    server_name your-domain.com;
    
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:3001/health;
        access_log off;
    }
}
```

启用站点：
```bash
sudo ln -s /etc/nginx/sites-available/image-gen-mcp /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 7. 配置防火墙

```bash
# 配置UFW防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 8. 启动应用

```bash
# 构建和启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 9. 配置SSL证书

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 设置自动更新
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 10. 设置系统服务

```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/image-gen-mcp.service
```

服务文件内容：
```ini
[Unit]
Description=Image Gen MCP Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/image-gen-mcp
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable image-gen-mcp
sudo systemctl start image-gen-mcp
```

## 🔧 运维管理

### 服务管理

```bash
# 启动服务
sudo systemctl start image-gen-mcp

# 停止服务
sudo systemctl stop image-gen-mcp

# 重启服务
sudo systemctl restart image-gen-mcp

# 查看状态
sudo systemctl status image-gen-mcp

# 查看日志
journalctl -u image-gen-mcp -f
```

### Docker管理

```bash
# 查看容器状态
docker ps

# 查看容器日志
docker logs image-gen-mcp -f

# 进入容器
docker exec -it image-gen-mcp bash

# 重启特定容器
docker restart image-gen-mcp

# 更新应用
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 监控访问

访问监控面板：
- Grafana: `http://your-domain.com:3000`
- Prometheus: `http://your-server-ip:9090`（仅localhost访问）

设置Grafana访问密码：
```bash
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### 备份管理

```bash
# 创建备份
./backup.sh

# 设置定时备份
crontab -e
# 添加: 0 2 * * * /opt/image-gen-mcp/backup.sh

# 恢复备份
cd /opt/backups/image-gen-mcp
tar -xzf storage_20240101_020000.tar.gz -C /opt/image-gen-mcp/
```

### 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose -f docker-compose.prod.yml build

# 3. 重启服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 清理旧镜像
docker image prune -f
```

## 📊 监控和指标

### 应用健康检查

```bash
# 健康检查
curl http://localhost:3001/health

# 查看应用指标
curl http://localhost:3001/metrics
```

### 系统资源监控

```bash
# 查看系统资源
htop
df -h
free -h

# 查看Docker资源使用
docker stats

# 查看网络连接
netstat -tulpn
```

### 日志管理

```bash
# 查看应用日志
tail -f /opt/image-gen-mcp/logs/app.log

# 查看Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 查看系统日志
sudo journalctl -f
```

## 🔒 安全最佳实践

### 1. 系统安全

```bash
# 安装Fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban

# 禁用root登录
sudo nano /etc/ssh/sshd_config
# 设置: PermitRootLogin no

# 使用密钥认证
# 在本地生成密钥对，上传公钥到服务器
```

### 2. 应用安全

- 定期更新系统和依赖
- 使用强密码和密钥
- 配置适当的防火墙规则
- 监控异常访问模式
- 定期备份重要数据

### 3. 网络安全

```bash
# 检查开放端口
sudo netstat -tulpn

# 检查防火墙状态
sudo ufw status verbose

# 检查失败登录尝试
sudo tail /var/log/auth.log
```

## 🚨 故障排除

### 常见问题

1. **容器无法启动**
   ```bash
   # 检查日志
   docker logs image-gen-mcp
   
   # 检查环境变量
   docker exec image-gen-mcp env
   ```

2. **端口占用**
   ```bash
   # 查看端口使用
   sudo netstat -tulpn | grep :3001
   
   # 停止占用进程
   sudo lsof -ti:3001 | xargs sudo kill -9
   ```

3. **磁盘空间不足**
   ```bash
   # 清理Docker
   docker system prune -a
   
   # 清理日志
   sudo journalctl --vacuum-time=3d
   ```

4. **SSL证书问题**
   ```bash
   # 测试证书
   sudo certbot certificates
   
   # 手动更新
   sudo certbot renew
   ```

### 应急恢复

1. **回滚到上一版本**
   ```bash
   # 使用备份镜像
   docker-compose -f docker-compose.prod.yml down
   docker tag image-gen-mcp:latest image-gen-mcp:backup
   docker tag image-gen-mcp:previous image-gen-mcp:latest
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **从备份恢复数据**
   ```bash
   # 停止服务
   docker-compose -f docker-compose.prod.yml down
   
   # 恢复数据
   cd /opt/backups/image-gen-mcp
   tar -xzf storage_backup.tar.gz -C /opt/image-gen-mcp/
   
   # 重启服务
   docker-compose -f docker-compose.prod.yml up -d
   ```

## 📞 支持和维护

### 定期维护任务

- **每日**: 检查服务状态和日志
- **每周**: 更新系统包，检查备份
- **每月**: 清理旧日志和镜像，性能评估
- **每季度**: 安全审计，依赖更新

### 性能优化

1. **调整Docker资源限制**
2. **优化Redis配置**
3. **配置Nginx缓存**
4. **监控API响应时间**

---

通过以上配置，你将获得一个**生产就绪的、安全的、可监控的**Image Gen MCP Server部署方案。
