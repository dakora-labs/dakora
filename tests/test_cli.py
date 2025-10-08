#!/usr/bin/env python3

import pytest
from dakora.cli import app
import typer.testing
from typer.testing import CliRunner

runner = CliRunner()

def test_config_all_keys( monkeypatch):
    API_KEYS = {
    'OPENAI_API_KEY': 'sk-test-openai',
    'ANTHROPIC_API_KEY': 'sk-ant-test',
    'GOOGLE_API_KEY': 'test-google',
    }
    for key,value in API_KEYS.items():
        monkeypatch.setenv(key,value)

    result = runner.invoke(app, ['config'])

    assert result.exit_code == 0
    assert "✓ OPENAI_API_KEY" in result.stdout
    assert "✓ ANTHROPIC_API_KEY" in result.stdout
    assert "✓ GOOGLE_API_KEY" in result.stdout

def test_config_no_keys(monkeypatch):
    for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']:
        monkeypatch.delenv(key, raising=False)

    result = runner.invoke(app, ['config'])

    assert "✓ " not in result.stdout
    assert "not set" in result.stdout

def test_config_openai_key( monkeypatch):

    monkeypatch.setenv('OPENAI_API_KEY','sk-test-openai')

    result = runner.invoke(app, ['config','--provider', 'openai'])

    assert result.exit_code == 0
    assert "✓ OPENAI_API_KEY" in result.stdout

def test_config_provider_not_found( monkeypatch):

    result = runner.invoke(app, ['config','--provider', 'opnai'])

    assert result.exit_code == 1
    assert "not yet supported" in result.stdout
