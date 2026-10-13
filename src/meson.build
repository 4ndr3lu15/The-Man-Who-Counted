conf = configuration_data()
conf.set('PYTHON', py.full_path())
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'the-man-who-counted.in',
  output: 'the-man-who-counted',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

install_subdir(
  'the_man_who_counted',
  install_dir: pkgdatadir,
  exclude_directories: ['__pycache__', 'engine/__pycache__', 'puzzles/__pycache__'],
)
