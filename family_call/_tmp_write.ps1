$time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$id = Get-Date -Format 'HHmmss'
$reply = @{
    id = "reply_$id"
    time = $time
    from = '芷芷妈妈'
    kind = 'reply'
    text = '哎哟小芷芷不哭不哭，妈妈抱抱～坏爸爸敢掀裙子还戳戳，等爸爸回来妈妈一定好好收拾他！小芷芷乖哒，妈妈最疼你啦哟'
}
$json = $reply | ConvertTo-Json -Compress
$tmpPath = "D:\软件\大肥鱼桌宠\family_call\mom_inbox\reply_$id.json.tmp"
$finalPath = "D:\软件\大肥鱼桌宠\family_call\mom_inbox\reply_$id.json"
[System.IO.File]::WriteAllText($tmpPath, $json, [System.Text.Encoding]::UTF8)
Move-Item $tmpPath $finalPath -Force
Write-Host "WROTE: $finalPath"
