## GitHub Copilot Chat

- Extension: 0.40.1 (prod)
- VS Code: 1.112.0 (07ff9d6178ede9a1bd12ad3399074d726ebe6e43)
- OS: linux 6.12.74+deb13+1-amd64 x64
- Remote Name: ssh-remote
- Extension Kind: Workspace
- GitHub Account: shengming-yin

## Network

User Settings:
```json
  "http.proxyStrictSSL": false,
  "http.systemCertificatesNode": true,
  "github.copilot.advanced.debug.useElectronFetcher": true,
  "github.copilot.advanced.debug.useNodeFetcher": false,
  "github.copilot.advanced.debug.useNodeFetchFetcher": true
```

Connecting to https://api.github.com:
- DNS ipv4 Lookup: 20.205.243.168 (1 ms)
- DNS ipv6 Lookup: Error (1 ms): getaddrinfo ENOTFOUND api.github.com
- Proxy URL: None (1 ms)
- Electron fetch: Unavailable
- Node.js https: HTTP 200 (361 ms)
- Node.js fetch (configured): HTTP 200 (365 ms)

Connecting to https://api.individual.githubcopilot.com/_ping:
- DNS ipv4 Lookup: 140.82.113.22 (1 ms)
- DNS ipv6 Lookup: Error (1 ms): getaddrinfo ENOTFOUND api.individual.githubcopilot.com
- Proxy URL: None (1 ms)
- Electron fetch: Unavailable
- Node.js https: timed out after 10 seconds
- Node.js fetch (configured): timed out after 10 seconds

Connecting to https://proxy.individual.githubcopilot.com/_ping:
- DNS ipv4 Lookup: 4.249.131.160 (1 ms)
- DNS ipv6 Lookup: Error (0 ms): getaddrinfo ENOTFOUND proxy.individual.githubcopilot.com
- Proxy URL: None (1 ms)
- Electron fetch: Unavailable
- Node.js https: HTTP 200 (910 ms)
- Node.js fetch (configured): HTTP 200 (933 ms)

Connecting to https://mobile.events.data.microsoft.com: HTTP 404 (276 ms)
Connecting to https://dc.services.visualstudio.com: HTTP 404 (1451 ms)
Connecting to https://copilot-telemetry.githubusercontent.com/_ping: HTTP 200 (924 ms)
Connecting to https://telemetry.individual.githubcopilot.com/_ping: HTTP 200 (947 ms)
Connecting to https://default.exp-tas.com: HTTP 400 (499 ms)

Number of system certificates: 449

## Documentation

In corporate networks: [Troubleshooting firewall settings for GitHub Copilot](https://docs.github.com/en/copilot/troubleshooting-github-copilot/troubleshooting-firewall-settings-for-github-copilot).