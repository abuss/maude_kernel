from __future__ import print_function

import sys
import os
import re
import subprocess
# import signal
import uuid

# from ipykernel.kernelbase import Kernel
# from pexpect import replwrap, EOF
# import pexpect

from metakernel import MetaKernel, ProcessMetaKernel, REPLWrapper, u
from metakernel.pexpect import which


__version__ = '0.0.1'

version_pat = re.compile(r'version (\d+(\.\d+)+)')


STDIN_PROMPT = '__stdin_prompt>'
STDIN_PROMPT_REGEX = re.compile(r'\A.+?%s|debug> ' % STDIN_PROMPT)
HELP_LINKS = [
    {
        'text': "Maude",
        'url': "http://maude.lcc.uma.es/manual271/maude-manual.html",
    },
    {
        'text': "Maude Kernel",
        'url': "https://github.com/abuss/maude_kernel",
    },

] + MetaKernel.help_links


class MaudeKernel(ProcessMetaKernel):
    implementation = 'Maude Kernel'
    implementation_version = __version__
    language = 'maude'
    help_links = HELP_LINKS

    _maude_engine = None
    
    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None

    kernel_json = {
        "argv": [sys.executable,
                 "-m", "maude_kernel",
                 "-f", "{connection_file}"],
        "display_name": "Maude",
        "mimetype": "text/x-maude",
        "language": "maude",
        "name": "maude",
    }

    
    @property
    def banner(self):
        if self._banner is None:
            msg = 'Maude Kernel v{} running Maude v{}'
            maude_version = subprocess.check_output(['maude.linux64',
                                                     '--version']).decode('utf-8')
            self._banner = msg.format(__version__,maude_version)
        return self._banner

    @property
    def language_info(self):
        return {'name': 'maude',
                'mimetype': 'text/x-maude',
                'file_extension': '.maude',
                'version': self.banner,
                'help_links': HELP_LINKS}

    @property
    def maude_engine(self):
        if self._maude_engine:
            return self._maude_engine
        self._maude_engine = MaudeEngine(error_handler=self.Error,
                                         stdin_handler=self.raw_input,
                                         stream_handler=self.Print,
                                         logger=self.log)
        return self._maude_engine

    def makeWrapper(self):
        """Start a Maude process and return a :class:`REPLWrapper` object.
        """
        return self.maude_engine.repl

    def do_execute_direct(self, code, silent=False):
        if code.strip() in ['quit', 'quit()', 'exit', 'exit()']:
            self._maude_engine = None
            self.do_shutdown(True)
            return
        val = ProcessMetaKernel.do_execute_direct(self, code, silent=silent)
        # if not silent:
        #     try:
        #         plot_dir = self.octave_engine.make_figures()
        #     except Exception as e:
        #         self.Error(e)
        #         return val
        #     if plot_dir:
        #         for image in self.octave_engine.extract_figures(plot_dir, True):
        #             self.Display(image)
        return val

    # passible not needed
    def get_kernel_help_on(self, info, level=0, none_on_fail=False):
        obj = info.get('help_obj', '')
        if not obj or len(obj.split()) > 1:
            if none_on_fail:
                return None
            else:
                return ""
        return self.maude_engine.eval('help %s' % obj, silent=True)
    
    def Print(self, *args, **kwargs):
        # Ignore standalone input hook displays.
        out = []
        for arg in args:
            if arg.strip() == STDIN_PROMPT:
                return
            if arg.strip().startswith(STDIN_PROMPT):
                arg = arg.replace(STDIN_PROMPT, '')
            out.append(arg)
        super(MaudeKernel, self).Print(*out, **kwargs)

    def raw_input(self, text):
        # Remove the stdin prompt to restore the original prompt.
        text = text.replace(STDIN_PROMPT, '')
        return super(MaudeKernel, self).raw_input(text)

    def get_completions(self, info):
        """
        Get completions from kernel based on info dict.
        """
        cmd = 'completion_matches("%s")' % info['obj']
        val = self.maude_engine.eval(cmd, silent=True)
        return val and val.splitlines() or []


class MaudeEngine(object):

    def __init__(self, error_handler=None, stream_handler=None,
                 stdin_handler=None, logger=None):
        self.logger = logger
        self.executable = self._get_executable()
        self.repl = self._create_repl()
        self.error_handler = error_handler
        self.stream_handler = stream_handler
        self.stdin_handler = stdin_handler
        # self._startup(plot_settings)


    def eval(self, code, timeout=None, silent=False):
        """Evaluate code using the engine.
        """
        stream_handler = None if silent else self.stream_handler
        if self.logger:
            self.logger.debug('Maude eval:')
            self.logger.debug(code)
        try:
            resp = self.repl.run_command(code.rstrip(),
                                         timeout=timeout,
                                         stream_handler=stream_handler,
                                         stdin_handler=self.stdin_handler)
            resp = resp.replace(STDIN_PROMPT, '')
            if self.logger and resp:
                self.logger.debug(resp)
            return resp
        except KeyboardInterrupt:
            return self._interrupt(True)
        except Exception as e:
            if self.error_handler:
                self.error_handler(e)
            else:
                raise e


    # def _startup(self, plot_settings):
    #     cwd = os.getcwd().replace(os.path.sep, '/')
    #     resp = self.eval('available_graphics_toolkits', silent=True)
    #     if 'gnuplot' in resp:
    #         self.eval("graphics_toolkit('gnuplot')", silent=True)
    #     self.eval('more off; source ~/.octaverc; cd("%s");' % cwd, silent=True)
    #     here = os.path.realpath(os.path.dirname(__file__))
    #     self.eval('addpath("%s")' % here.replace(os.path.sep, '/'))
    #     self.plot_settings = plot_settings

    def _create_repl(self):
        cmd = self.executable
        # if 'maude' not in cmd:
        #     version_cmd = [self.executable, '--version']
        #     version = subprocess.check_output(version_cmd).decode('utf-8')
        #     if 'version 4' in version:
        #         cmd += ' --no-gui'
        # # Interactive mode prevents crashing on Windows on syntax errors.
        # Delay sourcing the "~/.octaverc" file in case it displays a pager.
        # cmd += ' --interactive --quiet --no-init-file '
        cmd += ' -interactive -no-banner'

        # Add cli options provided by the user.
        cmd += os.environ.get('MAUDE_OPTIONS', '')

        orig_prompt = u('Maude>')
        change_prompt = u("PS1('{0}'); PS2('{1}')")

        repl = REPLWrapper(cmd, orig_prompt, change_prompt,
                           stdin_prompt_regex=STDIN_PROMPT_REGEX)
        if os.name == 'nt':
            repl.child.crlf = '\n'
        repl.interrupt = self._interrupt
        # Remove the default 50ms delay before sending lines.
        repl.child.delaybeforesend = None
        return repl

    def _interrupt(self, silent=False):
        if (os.name == 'nt'):
            msg = '** Warning: Cannot interrupt Maude on Windows'
            if self.stream_handler:
                self.stream_handler(msg)
            elif self.logger:
                self.logger.warn(msg)
            return self._interrupt_expect(silent)
        return REPLWrapper.interrupt(self.repl)

    def _interrupt_expect(self, silent):
        repl = self.repl
        child = repl.child
        expects = [repl.prompt_regex, child.linesep]
        expected = uuid.uuid4().hex
        repl.sendline('disp("%s");' % expected)
        if repl.prompt_emit_cmd:
            repl.sendline(repl.prompt_emit_cmd)
        lines = []
        while True:
            # Prevent a keyboard interrupt from breaking this up.
            while True:
                try:
                    pos = child.expect(expects)
                    break
                except KeyboardInterrupt:
                    pass
            if pos == 1:  # End of line received
                line = child.before
                if silent:
                    lines.append(line)
                else:
                    self.stream_handler(line)
            else:
                line = child.before
                if line.strip() == expected:
                    break
                if len(line) != 0:
                    # prompt received, but partial line precedes it
                    if silent:
                        lines.append(line)
                    else:
                        self.stream_handler(line)
        return '\n'.join(lines)

    def _get_executable(self):
        """Find the best maude executable.
        """
        executable = os.environ.get('MAUDE_EXECUTABLE', None)
        if not executable or not which(executable):
            if sys.platform == 'darwin':
                if which('maude.darwin64'):
                    executable = 'maude.darwin64'
            elif which('maude.linux64'):
                executable = 'maude.linux64'
            else:
                msg = ('Maude Executable not found, please add to path or set'
                       '"MAUDE_EXECUTABLE" environment variable')
                raise OSError(msg)
        executable = executable.replace(os.path.sep, '/')
        return executable
