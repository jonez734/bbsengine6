# Notes

- Installing/upgrading bbsengine6 requires building first:
  ```
  cd bbsengine6/py/src && python -m build
  pip install dist/bbsengine6-*.whl --force-reinstall
  ```

- pip install should install to Python 3.10 (mediapipe doesn't support 3.13+)
