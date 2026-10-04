def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_races_and_filter(client):
    assert len(client.get("/races").json()) == 2
    only_2023 = client.get("/races", params={"season": 2023}).json()
    assert [r["name"] for r in only_2023] == ["Australian Grand Prix"]


def test_race_detail_orders_results_with_dnf_last(client):
    body = client.get("/races/2023/1").json()
    assert [r["driver"]["code"] for r in body["results"]] == ["VER", "HAM", "PER"]
    assert body["results"][-1]["position"] is None


def test_race_not_found(client):
    assert client.get("/races/1999/1").status_code == 404


def test_drivers_list_and_search(client):
    names = [d["family_name"] for d in client.get("/drivers").json()]
    assert names == ["Hamilton", "Perez", "Verstappen"]
    assert len(client.get("/drivers", params={"q": "verst"}).json()) == 1


def test_driver_not_found(client):
    assert client.get("/drivers/nao_existe").status_code == 404


def test_driver_results(client):
    rows = client.get("/drivers/max_verstappen/results").json()
    assert len(rows) == 1
    assert rows[0]["race_name"] == "Australian Grand Prix"
    assert rows[0]["position"] == 1


def test_compare_available(client):
    codes = client.get("/compare/available", params={"season": 2023, "round": 1}).json()
    assert codes == ["PER", "VER"]


def test_compare_ok(client):
    resp = client.get("/compare", params={"season": 2023, "round": 1, "d1": "ver", "d2": "PER"})
    assert resp.status_code == 200
    body = resp.json()
    assert [d["code"] for d in body["drivers"]] == ["VER", "PER"]
    assert body["drivers"][0]["team"] == "red_bull"
    assert set(body["telemetry"]) == {"VER", "PER"}
    assert body["delta"][-1] == 2.0  # PER terminou a volta 2 s depois
    assert len(body["distance"]) == len(body["delta"]) == 5


def test_compare_same_driver_is_400(client):
    resp = client.get("/compare", params={"season": 2023, "round": 1, "d1": "VER", "d2": "ver"})
    assert resp.status_code == 400


def test_compare_driver_without_telemetry_is_404(client):
    resp = client.get("/compare", params={"season": 2023, "round": 1, "d1": "VER", "d2": "HAM"})
    assert resp.status_code == 404


def test_compare_invalid_session_is_422(client):
    resp = client.get("/compare", params={"season": 2023, "round": 1, "d1": "VER",
                                          "d2": "PER", "session": "X"})
    assert resp.status_code == 422
