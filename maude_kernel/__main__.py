# from ipykernel.kernelapp import IPKernelApp
# from .kernel import ImaudeKernel
# IPKernelApp.launch_instance(kernel_class=IMaudeKernel)

from .kernel import MaudeKernel

if __name__ == '__main__':
    MaudeKernel.run_as_main()
