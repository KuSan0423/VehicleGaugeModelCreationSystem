"""環境選択・引数保持・再起動ループ防止のテスト。"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rail_clearance import runtime

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.target=self.root/'.venv'
        self.root_patch=patch.object(runtime,'PROJECT_ROOT',self.root)
        self.root_patch.start();self.addCleanup(self.root_patch.stop)
    def create_venv_stub(self):
        executable=runtime.python_in(self.target)
        executable.parent.mkdir(parents=True)
        executable.touch();(self.target/'pyvenv.cfg').write_text('include-system-site-packages = false')
        return executable
    def test_absent_venv_uses_current_python(self):
        with patch.object(runtime.subprocess,'call') as call:
            runtime.use_project_venv(self.root/'launch.py')
        call.assert_not_called()
    def test_incomplete_venv_reports_setup(self):
        self.target.mkdir()
        with self.assertRaisesRegex(SystemExit,'不完全'):
            runtime.use_project_venv(self.root/'launch.py')
    def test_current_project_venv_does_not_restart(self):
        self.create_venv_stub()
        with patch.object(runtime.sys,'prefix',str(self.target)),patch.object(runtime.subprocess,'call') as call:
            runtime.use_project_venv(self.root/'launch.py')
        call.assert_not_called()
    def test_switch_keeps_arguments_exit_code_and_isolation(self):
        executable=self.create_venv_stub()
        with patch.object(runtime.sys,'prefix',str(self.root/'other')),patch.object(runtime.subprocess,'call',return_value=7) as call,patch.dict(
                os.environ,{'PYTHONHOME':'external','PYTHONPATH':'external','RAIL_CLEARANCE_VENV_REEXEC':''}):
            with self.assertRaises(SystemExit) as error:
                runtime.use_project_venv(self.root/'launch.py',['--config','設定.json','--no-render'])
        self.assertEqual(error.exception.code,7)
        command=call.call_args.args[0];env=call.call_args.kwargs['env']
        self.assertEqual(command,[str(executable),'-X','utf8',str(self.root/'launch.py'),'--config','設定.json','--no-render'])
        self.assertNotIn('PYTHONHOME',env);self.assertNotIn('PYTHONPATH',env)
        self.assertEqual(env['VIRTUAL_ENV'],str(self.target))
    def test_failed_switch_does_not_loop(self):
        self.create_venv_stub()
        with patch.object(runtime.sys,'prefix',str(self.root/'other')),patch.dict(os.environ,{'RAIL_CLEARANCE_VENV_REEXEC':str(self.target.resolve())}):
            with self.assertRaisesRegex(SystemExit,'切り替えに失敗'):
                runtime.use_project_venv(self.root/'launch.py')
    def test_missing_library_reports_setup(self):
        with patch.object(runtime.importlib,'import_module',side_effect=ImportError('PIL')):
            with self.assertRaisesRegex(SystemExit,'setup_venv.py'):runtime.ensure_dependencies()

if __name__=='__main__':unittest.main()
