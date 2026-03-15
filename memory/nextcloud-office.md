# Nextcloud 部署操作说明

## 服务器信息

- **位置**: 办公室服务器 (Dell PowerEdge R730)
- **内网地址**: http://192.168.40.123
- **SSH地址**: 3v763724f4.wicp.vip:40437
- **用户**: shangguanyun

## 部署方式

使用 Snap 安装 Nextcloud 32.0.6

## 常用命令

```bash
# 启动/停止
sudo snap start nextcloud
sudo snap stop nextcloud

# 查看状态
sudo snap services nextcloud

# 创建用户
sudo nextcloud.occ user:add <用户名> --display-name "<显示名称>"

# 修改密码
sudo nextcloud.occ user:resetpassword <用户名>

# 添加信任域名
sudo nextcloud.occ config:system:set trusted_domains 1 --value="192.168.40.123"

# 开启HTTPS (可选)
sudo nextcloud.enable-https lets-encrypt
```

## 初始配置

1. 首次访问 http://192.168.40.123 创建管理员账号
2. 登录后可在设置中添加用户、配置存储等
3. 可通过 WebDAV 访问文件： http://192.168.40.123/remote.php/dav/files/<用户名>/

## 数据位置

- 应用数据: /snap/nextcloud/current/htdocs/
- 用户数据: /var/snap/nextcloud/common/nextcloud/data/

## 注意事项

- 如遇端口被占用: `sudo systemctl stop apache2 && sudo systemctl disable apache2`
- Docker 已安装但无法拉取镜像（网络原因）
