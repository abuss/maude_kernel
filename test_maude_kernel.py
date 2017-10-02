"""Example use of jupyter_kernel_test, with tests for IPython."""

import sys
import unittest
import jupyter_kernel_test as jkt


class MaudeKernelTests(jkt.KernelTests):
    kernel_name = "maude"

    language_name = "maude"

    code_hello_world = "disp('hello, world')"

    # code_display_data = [
    #     {'code': '%plot -f png\nplot([1,2,3])', 'mime': 'image/png'},
    #     {'code': '%plot -f svg\nplot([1,2,3])', 'mime': 'image/svg+xml'}
    # ] if sys.platform == 'darwin' else []

    # completion_samples = [
    #     {
    #         'text': 'one',
    #         'matches': {'ones', 'onenormest'},
    #     },
    # ]

    code_page_something = "ones?"


if __name__ == '__main__':
    unittest.main()
