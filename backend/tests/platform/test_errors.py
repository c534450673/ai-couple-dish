from packages.platform.errors import unauthorized_result


def test_unauthorized_uses_compatible_envelope() -> None:
    response = unauthorized_result()
    assert response.status_code == 401
    assert response.body == '{"code":401,"message":"请先登录","data":null}'.encode()
