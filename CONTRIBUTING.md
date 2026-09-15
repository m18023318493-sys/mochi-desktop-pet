# Contributing

Thanks for helping Mochi grow.

1. Open an issue describing the change or bug.
2. Keep the runtime dependency-free unless there is a strong reason not to.
3. Put display-independent logic in `pet_core.py` so CI can test it without a desktop.
4. Run the tests and compile check before opening a pull request:

   ```powershell
   python -m unittest discover -s tests -v
   python -m py_compile pet_core.py mochi_pet.py
   ```

Please include your operating system, Python version, screen layout, and scaling percentage when reporting visual or positioning bugs.
