# MOBILE-07 controlled mobile network acceptance retry

```text
TASK_STATUS = BLOCKED
FINAL_VERDICT = BLOCKED_TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01_RETRY_01
BLOCKER_CODE = MOBILE_07_RETRY_BASELINE_NOT_SAFE
SECONDARY_BLOCKER = CURRENT_RUNTIME_MISSING_FOUR_ADDITIVE_READONLY_ROUTES
```

The real-device and network security gates passed. One authorized `SM-S928B`
running Android 16/API 36 used `wlan0` at `192.168.1.101/24`; the Windows host
used the Private `Беспроводная сеть` profile at `192.168.1.100/24`. The clean
server/mobile/desktop baselines were respectively `11ad50f`, `31f4ddf`, and
`e16e48f`.

The task temporarily created only this path:

```text
192.168.1.100:18765 -> 127.0.0.1:8765
firewall = TCP / Private / local 192.168.1.100:18765 / remote 192.168.1.101
```

There was no wildcard listener. Readonly loopback remained HTTP 200, Control
remained bound only to `127.0.0.1:8766`, and no PostgreSQL listener was present
on the host LAN. Android could connect to `18765` on Wi-Fi but could not connect
to host ports `8766` or `5432`. With Wi-Fi disabled and active cellular
interfaces present, the Readonly endpoint timed out; after reconnecting to the
same LAN the app recovered immediately.

Dashboard, Market, Setups, Funnel, Incidents, Help and Settings passed on the
real device. Background polling stopped and foreground refresh recovered. The
21-route Android GET matrix produced 17 HTTP 200, four HTTP 404 and zero 5xx.
The four unexpected 404 responses were:

- `GET /api/v1/analysis`
- `GET /api/v1/paper/orders?limit=50`
- `GET /api/v1/paper/fills?limit=50`
- `GET /api/v1/paper/journal?limit=50`

The current source implements these additive GET-only routes, but the current
localhost Readonly runtime still exposes the older 21-route contract. Analysis
therefore failed and PAPER remained partial. Deploying the additive contract
was outside the authorized MOBILE-07 mutation scope, so the task stopped
without accepting the LAN configuration or authorizing MOBILE-08.

The mobile debug variant received a debug-only cleartext override. The merged
release manifest remains `usesCleartextTraffic=false`; 215 unit tests, Kotlin
compile, resources, debug APK build and lint passed. The APK was installed with
`adb install -r`, and the Control URL remained empty.

After the blocked verdict, the Android Readonly URL was cleared and both
task-created Windows objects were removed. Final postcheck found no task
portproxy, no task firewall rule, no listener on `18765`, Readonly loopback
health/dashboard HTTP 200, and Control still loopback-only. Control generation
remained 6, canary remained `WAITING_FOR_ELIGIBLE_APPROVAL`, and LIVE remained
off. No POST, SQL, trading, private Binance, canary, LIVE, router, UPnP, DMZ,
DNS, reverse-proxy, tunnel, service restart, database mutation, or push occurred.

## Security matrix at test time

| Surface | Host local? | Android on trusted Wi-Fi? | Public/mobile data? | Expected | Evidence |
|---|---|---|---|---|---|
| Existing Readonly `127.0.0.1:8765` | Yes | Via dedicated listener | No | Yes/indirect/no | Local HTTP 200; app and Android curl; cellular timeout |
| Temporary mobile listener `192.168.1.100:18765` | Yes | Yes | No | Yes/yes/no | Exact listener/firewall; Android connect; off-LAN timeout |
| Control `127.0.0.1:8766` | Yes | No | No | Yes/no/no | Host listener and Android TCP timeout |
| PostgreSQL `5432` | No host LAN listener observed | No | No | As before/no/no | Host listener check and Android TCP timeout |

## Exact rollback

The rollback used the task identity only:

```powershell
Remove-NetFirewallRule -DisplayName 'TRADERS Mobile Readonly API LAN'
netsh interface portproxy delete v4tov4 listenaddress=192.168.1.100 listenport=18765 protocol=tcp
```

The Android Settings Readonly URL was cleared and saved. A later accepted retry
may recreate the same exact-address path only after the additive Readonly routes
are deployed and the fresh device/host IP facts are revalidated.
