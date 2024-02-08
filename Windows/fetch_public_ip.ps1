# fetch_public_ip.ps1
$PublicIP = (Invoke-RestMethod -Uri "https://api.ipify.org?format=text")
Write-Output $PublicIP
