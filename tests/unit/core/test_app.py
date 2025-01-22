from tablettop_bot.src.tablettop_bot.core.games import App


def test_app_run():
    # Arrange
    app = App("test parameter")

    # Act
    response = app.run("test message")

    # Assert
    assert response == "Message text: test message\nApp's parameter: test parameter"
