# MOBILE-07 controlled mobile network access acceptance retry 02

```text
TASK_ID = TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01_RETRY_02
AUDITED_AT_UTC = 2026-08-17T19:02:56Z
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01_RETRY_02_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
```

## Accepted scope

One authorized real `SM-S928B` running Android 16/API 36 was connected through
`wlan0` at `192.168.1.101/24`. The Windows host remained on the Private
`Беспроводная сеть` profile at `192.168.1.100/24`. Server, mobile and desktop
repositories were clean before acceptance. The already accepted Readonly
runtime exposed the required 25 GET and zero write routes on loopback.

The task installed the already built debug APK and created only this controlled
path:

```text
portproxy = 192.168.1.100:18765 -> 127.0.0.1:8765
firewall = ENABLED ALLOW TCP PRIVATE
firewall_local = 192.168.1.100:18765
firewall_remote = 192.168.1.101
edge_traversal = NO
```

The listener is exact-address, not wildcard. No Control, PostgreSQL, router,
UPnP, DMZ, public DNS, reverse proxy or tunnel path was created. The Android
debug app retains `http://192.168.1.100:18765` as its Readonly URL and retains
an empty Control URL. The merged release manifest remains
`usesCleartextTraffic=false`; only the debug manifest permits cleartext for the
controlled private-LAN path.

## Real-device acceptance

The Android GET matrix completed with 21 HTTP 200 responses, zero unexpected
4xx and zero 5xx:

```text
/api/v1/health
/api/v1/dashboard
/api/v1/trading-universe
/api/v1/markets
/api/v1/markets/BTCUSDT
/api/v1/analysis
/api/v1/analysis/BTCUSDT
/api/v1/setups?limit=50
/api/v1/trading/funnel
/api/v1/incidents?limit=50
/api/v1/paper/readiness
/api/v1/paper/account
/api/v1/paper/runtime/status
/api/v1/paper/control/status
/api/v1/paper/positions?limit=50
/api/v1/paper/trades?limit=50
/api/v1/paper/orders?limit=50
/api/v1/paper/fills?limit=50
/api/v1/paper/journal?limit=50
/api/v1/paper/reconciliation
/api/v1/paper/trading-criteria
```

Dashboard, Market, Analysis, Setups, Funnel, Incidents, PAPER, Help and
Settings all loaded real data. Dashboard showed authoritative `OK`, Market Data
`60/60`, WAL/PITR ready and LIVE off. Analysis used the bounded aggregate route;
PAPER orders, fills and journal loaded successfully. Foreground recovery
returned the dashboard to `Подключено` and a zero-second successful update.

With Wi-Fi disabled, `wlan0` was absent while a cellular `rmnet_data*` IPv4
interface remained active. Android curl to the LAN endpoint returned code `000`
after its bounded timeout. The app preserved its last-known Market data while
the successful-update age increased from 5 to 25 seconds. After Wi-Fi returned
to `192.168.1.101/24`, the app recovered to a zero-second update and Android
curl returned HTTP 200. Android TCP attempts to host LAN ports 8766 and 5432
timed out.

## Validation and invariance

```text
MOBILE_STATUS_COMMIT = 3ec5903fa0efbfc3368924a834bd26405e0d15b6
MOBILE_UNIT_TESTS = 215_PASS_0_FAIL_0_SKIP
MOBILE_COMPILE_RESOURCES_DEBUG_APK_LINT = PASS
DEBUG_APK_SHA256 = AECFBEC32E6944F5E2894F2BCF40056E4B24624F0CD13A0E623ED791A5A998B0
MERGED_RELEASE_CLEARTEXT = FALSE
ANDROID_GET_MATRIX = 21_HTTP200_0_UNEXPECTED4XX_0_HTTP5XX
ANDROID_SCREEN_MATRIX = 9_OF9_PASS
CELLULAR_NEGATIVE = PASS_TIMEOUT_WITH_ACTIVE_CELLULAR_IPV4
WIFI_RECONNECT = PASS_HTTP200_APP_ZERO_SECOND_REFRESH
ANDROID_CONTROL_AND_POSTGRESQL = DENIED_TIMEOUT_PASS
DESKTOP_REGRESSION = 1434_PASS_2_SKIP_3020_SUBTESTS_PLUS_FOCUSED_TK_GUI_1_PASS_IN_PROJECT_VENV
```

The first desktop run used system Python and had one environment-only Tcl/Tk
installation failure after 1,434 tests and 3,020 subtests passed; the exact GUI
test passed in the project's established virtual environment. Local desktop
Readonly access stayed HTTP 200.

Readonly, orchestrator, market-data, Control and PostgreSQL containers retained
their identities and restart count zero. A boundary-transition sample briefly
reported `BOUNDARY_GRACE_EXPIRED` with WAL/PITR projection false, then
self-recovered without action to `OK/CURRENT`, WAL true, PITR true and lineage
valid. PostgreSQL remained healthy at the previously accepted Alembic revision
`0015_trading_universe_activation`. Control remained healthy and ARMED at
generation 6. Canary `6f9858cd-f6b1-4c7f-810c-fccc1065bb9d` remained
`WAITING_FOR_ELIGIBLE_APPROVAL` with zero commands and zero open positions.
PAPER mutation readiness remained false and LIVE remained disabled.

No POST, SQL, migration, DDL, DML, grant, service restart, trading action,
private Binance call, Control action, canary transition, LIVE change, router
mutation, public exposure, source change or push occurred.

## Accepted network matrix

| Surface | Host local | Authorized Android Wi-Fi | Cellular/public | Result |
|---|---:|---:|---:|---|
| Readonly `127.0.0.1:8765` | Yes | Via exact listener | No | PASS |
| Mobile Readonly `192.168.1.100:18765` | Yes | Yes, exact phone IP | No | PASS |
| Control `127.0.0.1:8766` | Yes | No | No | PASS |
| PostgreSQL host port `5432` | No LAN listener | No | No | PASS |

## Exact rollback

The accepted path may be removed without touching any other network object:

```powershell
Remove-NetFirewallRule -DisplayName 'TRADERS Mobile Readonly API LAN'
netsh interface portproxy delete v4tov4 listenaddress=192.168.1.100 listenport=18765 protocol=tcp
```

Then clear the Android Readonly URL through Settings. Do not populate the
Control URL. MOBILE-08 is not authorized by this acceptance.

```text
NEXT_ACTION = MOBILE_08_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION
MOBILE_08_AUTHORIZED = NO
PUSHED = NO
```
