# scripts/keep_tunnel.ps1
# Auto-reconnecting SSH reverse tunnel for vSET Ollama bridge
param (
    [string]$KeyPath = "$HOME\.ssh\vset-key.pem",
    [string]$HostIp = "13.206.229.40",
    [string]$User = "ubuntu",
    [int]$RemotePort = 11434,
    [int]$LocalPort = 11434
)

Write-Host "Starting persistent reverse SSH tunnel to $User@$HostIp ($RemotePort -> 127.0.0.1:$LocalPort)..."
while ($true) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Connecting SSH tunnel..."
    try {
        & ssh -i "$KeyPath" -o "StrictHostKeyChecking=no" -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" -o "ExitOnForwardFailure=yes" -N -R 0.0.0.0:${RemotePort}:127.0.0.1:${LocalPort} "${User}@${HostIp}"
    } catch {
        Write-Warning "SSH process encountered error: $_"
    }
    Write-Warning "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Tunnel disconnected. Reconnecting in 5 seconds..."
    Start-Sleep -Seconds 5
}
