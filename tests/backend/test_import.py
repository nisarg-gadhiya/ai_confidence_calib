def test_backend_imports():

    from app.main import app

    assert (
        app.title
        == "AI Confidence Calibration"
    )