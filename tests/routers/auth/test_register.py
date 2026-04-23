from unittest.mock import AsyncMock
import uuid
import pytest

from api.routers.auth.service import AuthService


@pytest.mark.asyncio
async def test_register_user_created_successfully(client):
    """
    Tests that a user can register with valid credentials
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Secure!Pass123!",
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_user_sends_email(event_loop, client):
    """
    Tests that a user receives verification email after registering
    """
    mock_email_service = AsyncMock()
    AuthService._em_service = mock_email_service
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Secure!Pass123!",
        },
    )

    assert response.status_code == 201
    mock_email_service.send_email.assert_awaited_once()
    args, kwargs = mock_email_service.send_email.await_args

    assert args[0] == "test@example.com"
    assert args[1] == "Verify your email for Gova"


@pytest.mark.asyncio
async def test_register_invalid_username_too_short(client):
    """
    Tests that a user cannot register with username less than 3 characters
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "ab",
            "email": "test@example.com",
            "password": "Secure!Pass123!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_password_too_short(client):
    """
    Tests that a user cannot register with password less than 8 characters
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Short1!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_password_no_uppercase(client):
    """
    Tests that a user cannot register with password missing uppercase
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "lowercase123!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_missing_special(client):
    """
    Tests that a user cannot register with password missing special char
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Lowercase123",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_password_too_short(client):
    """
    Tests that a user cannot register with password less than 8 characters
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Short1!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_password_no_uppercase(client):
    """
    Tests that a user cannot register with password missing uppercase
    """
    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "lowercase123!",
        },
    )

    assert response.status_code == 422
