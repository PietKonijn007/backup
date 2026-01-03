# Troubleshooting Commands for EC2 Instance

You're already logged into the EC2 instance. Run these commands directly:

## 1. Check Service Logs

```bash
sudo journalctl -u backup-daemon -n 50 --no-pager
```

## 2. Check if .env File Exists

```bash
ls -la /opt/backup-app/.env
```

## 3. If .env Missing, Retrieve from Parameter Store

```bash
aws ssm get-parameter --name "/backup-app/env" --with-decryption --query "Parameter.Value" --output text --region us-east-1 | sudo tee /opt/backup-app/.env
sudo chown backupapp:backupapp /opt/backup-app/.env
sudo chmod 600 /opt/backup-app/.env
```

## 4. Check rclone Configuration

```bash
sudo ls -la /home/backupapp/.config/rclone/
```

## 5. Test Application Manually

```bash
cd /opt/backup-app
sudo -u backupapp /opt/backup-app/venv/bin/python app.py
# Press Ctrl+C after checking if it starts correctly
```

## 6. Check Systemd Service File

```bash
cat /etc/systemd/system/backup-daemon.service
```

## 7. Fix Common Issues

### If the working directory is wrong:
```bash
sudo sed -i 's|WorkingDirectory=.*|WorkingDirectory=/opt/backup-app|' /etc/systemd/system/backup-daemon.service
sudo systemctl daemon-reload
```

### If the ExecStart path is wrong:
```bash
sudo sed -i 's|ExecStart=.*|ExecStart=/opt/backup-app/venv/bin/python /opt/backup-app/app.py|' /etc/systemd/system/backup-daemon.service
sudo systemctl daemon-reload
```

## 8. Restart the Service

```bash
sudo systemctl restart backup-daemon
sudo systemctl status backup-daemon
```

## 9. View Real-time Logs

```bash
sudo journalctl -u backup-daemon -f
```

## 10. Check if App is Listening

```bash
sudo netstat -tlnp | grep 8080
# or
curl http://localhost:8080
```

## Quick Fix Script

Run all fixes at once:

```bash
# Ensure .env exists
if [ ! -f /opt/backup-app/.env ]; then
    aws ssm get-parameter --name "/backup-app/env" --with-decryption --query "Parameter.Value" --output text --region us-east-1 | sudo tee /opt/backup-app/.env
    sudo chown backupapp:backupapp /opt/backup-app/.env
    sudo chmod 600 /opt/backup-app/.env
fi

# Fix service file paths
sudo cp /opt/backup-app/systemd/backup-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart backup-daemon
sudo systemctl status backup-daemon
```
