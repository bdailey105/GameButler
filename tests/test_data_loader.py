import pytest
import pandas as pd
import os
from src.data_loader import load_steam_library, load_external_library

# Get absolute path to the sample data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_CSV_PATH = os.path.join(BASE_DIR, 'data', 'sample_library.csv')
REAL_CSV_PATH = os.path.join(BASE_DIR, 'data', 'real_library_sample.csv')

def test_load_steam_library_success():
    """Test loading a valid internal format CSV file."""
    df = load_steam_library(SAMPLE_CSV_PATH)
    assert not df.empty
    assert 'Name' in df.columns
    assert 'AppID' in df.columns

def test_load_real_library_format():
    """Test loading the user's specific export format."""
    df = load_steam_library(REAL_CSV_PATH)
    assert not df.empty
    assert 'Name' in df.columns
    assert 'AppID' in df.columns
    assert 'Playtime_Forever' in df.columns
    
    # Check normalization
    assert df.iloc[0]['Name'] == '(the) Gnorp Apologue'
    # Hours was empty in csv -> 0 -> 0 mins
    assert df.iloc[0]['Playtime_Forever'] == 0 
    assert df.iloc[0]['Genre'] == 'Unknown'

def test_load_steam_library_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_steam_library("non_existent_file.csv")

def test_load_external_library_success(tmp_path):
    csv_path = tmp_path / "external.csv"
    csv_path.write_text(
        "title,platform,source,external_id,genre,tags,playtime_minutes\n"
        "Zelda: TotK,switch,nintendo_export,abc123,Adventure,Open World,600\n"
    )

    df = load_external_library(str(csv_path))
    assert not df.empty
    assert list(df.columns) == ["title", "platform", "source", "external_id", "genre", "tags", "playtime_minutes"]
    assert df.iloc[0]["title"] == "Zelda: TotK"
    assert df.iloc[0]["platform"] == "switch"
    assert df.iloc[0]["source"] == "nintendo_export"

def test_load_external_library_fills_missing_optional_columns(tmp_path):
    csv_path = tmp_path / "external.csv"
    csv_path.write_text("title,platform,source\nMetroid,switch,nintendo_export\n")

    df = load_external_library(str(csv_path))
    for optional in ("external_id", "genre", "tags", "playtime_minutes"):
        assert optional in df.columns
        assert df.iloc[0][optional] is None

def test_load_external_library_missing_required_headers_names_them(tmp_path):
    csv_path = tmp_path / "external.csv"
    csv_path.write_text("title,platform\nMetroid,switch\n")

    with pytest.raises(ValueError, match="source"):
        load_external_library(str(csv_path))

def test_load_external_library_header_case_insensitive(tmp_path):
    csv_path = tmp_path / "external.csv"
    csv_path.write_text(" Title , Platform , Source \nMetroid,switch,nintendo_export\n")

    df = load_external_library(str(csv_path))
    assert list(df.columns[:3]) == ["title", "platform", "source"]
    assert df.iloc[0]["title"] == "Metroid"

def test_load_external_library_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_external_library("non_existent_external_file.csv")