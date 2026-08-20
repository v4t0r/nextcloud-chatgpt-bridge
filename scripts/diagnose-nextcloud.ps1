param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$BaseUrl,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Username,

    [string]$RootPath = "/ChatGPT",

    [switch]$WriteTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$securePassword = Read-Host "Nextcloud app password" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

    $env:NEXTCLOUD_BASE_URL = $BaseUrl.TrimEnd('/')
    $env:NEXTCLOUD_USERNAME = $Username
    $env:NEXTCLOUD_APP_PASSWORD = $plainPassword
    $env:NEXTCLOUD_ROOT_PATH = $RootPath
    $env:NEXTCLOUD_VERIFY_TLS = "true"
    $env:NEXTCLOUD_ALLOW_INSECURE_HTTP = "false"

    $arguments = @("-m", "nextcloud_chatgpt_bridge.diagnostics")
    if ($WriteTest) {
        $arguments += "--write-test"
    }

    & python @arguments
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:NEXTCLOUD_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:NEXTCLOUD_USERNAME -ErrorAction SilentlyContinue
    Remove-Item Env:NEXTCLOUD_APP_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:NEXTCLOUD_ROOT_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:NEXTCLOUD_VERIFY_TLS -ErrorAction SilentlyContinue
    Remove-Item Env:NEXTCLOUD_ALLOW_INSECURE_HTTP -ErrorAction SilentlyContinue

    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plainPassword = $null
    $securePassword = $null
}
