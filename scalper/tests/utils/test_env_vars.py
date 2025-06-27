from utils import get_env_var


def test_get_env_var(monkeypatch, tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('FOO=bar\n')
    monkeypatch.setattr('utils.env_vars.ROOT_DIR', tmp_path)
    val = get_env_var('FOO')
    assert val == 'bar'
