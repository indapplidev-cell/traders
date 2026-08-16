from app.engine_market_data.binance_public_rest import BinancePublicRestClient


def test_default_origin_is_public_market_data_only() -> None:
    assert BinancePublicRestClient.BASE_URL == "https://data-api.binance.vision"


class Response:
    status_code = 200

    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return self.payload


class Transport:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url: str, *, params: dict | None = None) -> Response:
        self.calls.append((url, params))
        return Response(self.payload)


def test_rest_payload_maps_to_closed_rest_candle_without_network() -> None:
    transport = Transport([[0, "10", "12", "9", "11", "5", 59_999, "52", 3, "2", "20", "0"]])
    client = BinancePublicRestClient(transport=transport)
    result = client.fetch_klines("btcusdt", "1m", 0, 59_999, 1)
    assert len(result) == 1
    assert result[0].is_closed is True
    assert result[0].source == "rest"
    assert transport.calls[0][1] == {
        "symbol": "BTCUSDT", "interval": "1m", "limit": 1, "startTime": 0, "endTime": 59_999,
    }


def test_public_server_time_mapping() -> None:
    client = BinancePublicRestClient(transport=Transport({"serverTime": 1234}))
    assert client.fetch_server_time_ms() == 1234
