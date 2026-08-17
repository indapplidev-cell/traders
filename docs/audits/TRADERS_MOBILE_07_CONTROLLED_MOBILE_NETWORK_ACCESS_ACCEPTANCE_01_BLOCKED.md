# MOBILE-07 controlled mobile network access audit

```text
TASK_ID = TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01
AUDITED_AT_UTC = 2026-08-17T15:56:47.268Z
TASK_STATUS = BLOCKED
FINAL_VERDICT = BLOCKED_TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01
BLOCKER_CODE = REAL_ANDROID_DEVICE_NOT_AVAILABLE_FOR_MOBILE_NETWORK_ACCEPTANCE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = REAL_ANDROID_DEVICE_REQUIRED_BEFORE_NETWORK_MUTATION
```

## Proven preflight

All three required repositories were clean. The actual branches, commits and
trees matched the supplied reference state:

```text
SERVER = feature/engine-platform fff017c1879b3463fedd8ceca76a3012c2928c74 tree dc094e49040b3359b6917ee4335e55395879b5b9 CLEAN
MOBILE = main 81b714b8a02ce5310adc4c034e7a466ec6930afc tree a1873e0a5bb77d1cb5e3645f5a8516c73ee8dfe7 CLEAN
DESKTOP = main e16e48fdb78e605d0c3c6232946537ee241a8708 tree 8a8d1ebea35284aa79037325e7eaa63b62eeaa54 CLEAN
```

The trusted host LAN was unambiguous:

```text
HOST_LAN_INTERFACE_NAME = Беспроводная сеть
HOST_LAN_IPV4 = 192.168.1.100
HOST_LAN_PREFIX = 24
HOST_NETWORK_PROFILE = Private
HOST_LAN_ADDRESS_PRIVATE = YES
```

Required local service checks passed without exposing response bodies or
credentials:

```text
READONLY_LOCAL_ENDPOINT = 127.0.0.1:8765
CONTROL_LOCAL_ENDPOINT = 127.0.0.1:8766
POSTGRESQL_LOCAL_ENDPOINT_OR_BIND = NO_HOST_TCP_LISTENER_OBSERVED_ON_5432
LOCAL_READONLY_API_HEALTH_BEFORE = PASS_HEALTH_200_DASHBOARD_200
LOCAL_READONLY_API_HEALTH_AFTER = PASS_HEALTH_200_DASHBOARD_200
LOCAL_DESKTOP_READONLY_PATH_PRESERVED = YES
```

No existing v4-to-v4 Windows portproxy was present. TCP/UDP port `18765` was
free when checked and is only a candidate; it was not reserved or configured.
No enabled inbound allow rule matching ports 8765, 8766, 5432, or an Any-port
filter was found. The dedicated rule name was absent before and after preflight.

## Blocking device gate

`adb devices -l` returned no attached or authorized device. The diagnostic ADB
daemon started by that command was stopped before audit completion. Without an
accessible real Android device, its LAN IPv4 and membership in the intended LAN
could not be established. Therefore an exact-phone firewall scope could not be
proved, and no fallback subnet rule was authorized or created.

The missing device also prevents the mandatory real-device health, route,
screen, request-count, lifecycle, Wi-Fi reconnect, mobile-data negative,
Control negative, and PostgreSQL negative tests. Emulator or host-only results
were not promoted to acceptance.

## Source and security observations

The deployed Readonly API exposes no application authentication contract in
the inspected source; MOBILE-07 must therefore rely on the exact private host
listener plus narrow firewall remote scope. Existing authentication was not
weakened.

Android Settings already provides an explicit user-configured Readonly URL and
rejects embedded URI credentials. No automatic discovery or LAN port scanning
exists. The main Android manifest has `android:usesCleartextTraffic="false"`,
so release cleartext remains disabled. No debug cleartext exception was added
because host networking and real-device acceptance did not begin.

## Mutation and exposure result

```text
SERVER_SOURCE_CHANGED = NO
MOBILE_SOURCE_CHANGED = NO
DESKTOP_SOURCE_CHANGED = NO
SERVER_NETWORK_CONFIGURATION_CHANGED = NO
SERVER_FIREWALL_CHANGED = NO
MOBILE_READONLY_FORWARDER_CREATED = NO
FIREWALL_RULE_CREATED_BY_TASK = NO
EXISTING_READONLY_API_BIND_CHANGED = NO
MOBILE_READONLY_LISTENER_WILDCARD = NO_LISTENER_CREATED
CONTROL_API_FIREWALL_EXPOSURE_CREATED = NO
ROUTER_PORT_FORWARD_CREATED = NO
UPNP_ENABLED_BY_TASK = NO
DMZ_CHANGE_BY_TASK = NO
PUBLIC_DNS_CREATED = NO
PUBLIC_REVERSE_PROXY_CREATED = NO
PUBLIC_TUNNEL_CREATED = NO
INTERNET_REACHABILITY_INTENDED = NO
WINDOWS_FIREWALL_DISABLED_BY_TASK = NO
THIRD_PARTY_NETWORK_SOFTWARE_INSTALLED = NO
CONTROL_API_POST_CALLS_BY_TASK = 0
CONTROL_ACTIONS_BY_TASK = 0
PRODUCTION_DATABASE_MUTATIONS_BY_TASK = 0
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
LIVE_STATE_CHANGED_BY_TASK = NO
CANARY_STATE_CHANGED_BY_TASK = NO
CONTROL_GENERATION_CHANGED_BY_TASK = NO
```

## Acceptance matrix at blocked stop

| Surface | Host local reachable? | Android reachable? | Public/mobile-data reachable? | Expected? |
|---|---:|---:|---:|---|
| Existing Readonly `127.0.0.1:8765` | YES | NOT TESTED; no mobile listener | NO LISTENER INTENDED | Local YES only |
| Candidate mobile Readonly `192.168.1.100:18765` | NO; not created | NO; not created | NO; not created | Must become Android-only after retry |
| Control API `127.0.0.1:8766` | YES | NOT TESTED; loopback-only host bind observed | NO PUBLIC BIND OBSERVED | Android/public NO |
| PostgreSQL host port `5432` | NO host listener observed | NOT TESTED | NO HOST LISTENER OBSERVED | Android/public NO |

This matrix records the fail-closed stop state, not MOBILE-07 acceptance.

## Retry and rollback

Retry only after a real Android phone is attached/authorized for testing and
connected to the expected `192.168.1.0/24` private Wi-Fi. Obtain its actual LAN
IPv4 from the device, re-run all preflight gates, then prefer an exact-phone-IP
Private-profile rule.

No rollback was required because no listener, firewall rule, Android setting,
source configuration, router configuration, or public path was created. If a
later retry creates the approved configuration, its exact rollback is:

```text
netsh interface portproxy delete v4tov4 listenaddress=192.168.1.100 listenport=18765
Remove-NetFirewallRule -DisplayName "TRADERS Mobile Readonly API LAN"
Reset or replace the Android Readonly URL in Settings; do not populate Control URL.
```

After rollback, re-check `GET http://127.0.0.1:8765/api/v1/health` and confirm
that no listener remains on `192.168.1.100:18765`.

```text
NEXT_ACTION = RETRY_TRADERS_MOBILE_07_AFTER_REAL_ANDROID_DEVICE_IS_AVAILABLE
PUSHED = NO
```
