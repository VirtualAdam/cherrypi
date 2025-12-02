# find_pi.ps1
# Scans the local subnet to find Raspberry Pi devices based on MAC address.
# Uses .NET Ping class for parallel execution.

Write-Host "Identifying local network..."
$localIpConfig = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match 'Wi-Fi|Ethernet' -and $_.IPAddress -notmatch '^169' -and $_.IPAddress -notmatch '^127' } | Select-Object -First 1

if (-not $localIpConfig) {
    Write-Error "Could not determine local IP address. Ensure you are connected to a network."
    exit
}

$localIp = $localIpConfig.IPAddress
$subnet = $localIp.Substring(0, $localIp.LastIndexOf('.'))
Write-Host "Scanning Subnet: $subnet.0/24"
Write-Host "Launching parallel pings (this will be fast)..."

# Create and launch ping tasks
$tasks = 1..254 | ForEach-Object {
    $ip = "$subnet.$_"
    $ping = New-Object System.Net.NetworkInformation.Ping
    # 500ms timeout for each ping
    $ping.SendPingAsync($ip, 500)
}

# Wait for all pings to complete or timeout after 1 second total
try {
    [System.Threading.Tasks.Task]::WaitAll($tasks, 1000)
} catch {
    # Suppress errors from timeouts/cancellations
}

Write-Host "Analyzing ARP table..."
# Raspberry Pi MAC Address OUIs
$piOuis = @("b8-27-eb", "dc-a6-32", "e4-5f-01", "28-cd-c1", "d8-3a-dd", "e4-5f-01")

$arpOutput = arp -a
$found = $false

foreach ($line in $arpOutput) {
    foreach ($oui in $piOuis) {
        if ($line -match $oui) {
            Write-Host "FOUND RASPBERRY PI: $line" -ForegroundColor Green
            $found = $true
        }
    }
}

if (-not $found) {
    Write-Host "No Raspberry Pi specific MAC addresses found." -ForegroundColor Yellow
    Write-Host "Showing all dynamic ARP entries:"
    $arpOutput | Select-String "dynamic"
    
    Write-Host "`nChecking found devices for open SSH port (22)..."
    $ips = $arpOutput | Select-String "dynamic" | ForEach-Object { $_.ToString().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)[0] }
    
    foreach ($ip in $ips) {
        if ($ip -match "^192\.|^10\.|^172\.") {
            try {
                $socket = New-Object System.Net.Sockets.TcpClient
                $connect = $socket.BeginConnect($ip, 22, $null, $null)
                # Increased timeout to 1000ms (1 second) for slower devices/WiFi
                $wait = $connect.AsyncWaitHandle.WaitOne(1000, $false)
                if ($wait -and $socket.Connected) {
                    $stream = $socket.GetStream()
                    $buffer = New-Object byte[] 1024
                    $bytesRead = $stream.Read($buffer, 0, 1024)
                    $banner = [System.Text.Encoding]::ASCII.GetString($buffer, 0, $bytesRead).Trim()
                    
                    Write-Host "  [OPEN SSH] $ip - $banner" -ForegroundColor Cyan
                    $socket.Close()
                }
            } catch {}
        }
    }
}

Write-Host "`nScan Complete."
