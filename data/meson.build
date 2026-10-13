install_data(
  app_id + '.desktop',
  install_dir: get_option('datadir') / 'applications',
)

install_data(
  app_id + '.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo',
)

install_subdir(
  'icons/hicolor',
  install_dir: get_option('datadir') / 'icons',
)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('validate-desktop', desktop_file_validate, args: [files(app_id + '.desktop')])
endif

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-metainfo', appstreamcli,
    args: ['validate', '--no-net', '--explain', files(app_id + '.metainfo.xml')])
endif
