import pytest


@pytest.mark.asyncio
async def test_login_user_successfully(client):
    """
    Tests that a user can log in with valid credentials
    """


@pytest.mark.asyncio
async def test_login_user_invalid_email(client):
    """
    Tests that a user cannot log in with invalid email
    """


@pytest.mark.asyncio
async def test_login_user_invalid_password(client):
    """
    Tests that a user cannot log in with invalid password
    """


@pytest.mark.asyncio
async def test_login_user_unverified(client):
    """
    Tests that a user cannot log in if their account is unverified
    """
