project(
  'the-man-who-counted',
  version: 'pre-alpha.1',
  meson_version: '>= 1.0.0',
  license: 'MIT',
)

gnome = import('gnome')
python = import('python')

app_id = 'io.github._4ndr3lu15.TheManWhoCounted'
pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
py = python.find_installation('python3')

subdir('data')
subdir('src')

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
