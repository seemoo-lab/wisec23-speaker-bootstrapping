pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'linux_client_gui')
gnome = import('gnome')

gnome.compile_resources('linux_client_gui',
  'linux_client_gui.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'linux_client_gui.in',
  output: 'linux_client_gui',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

linux_client_gui_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'pairing.py',
  'acoustic.py',
  'ecdh.py',
  'sock_cli.py',
  'config.py',
  'database.py',
  'control.py',
  'listupdate.py',
  'wifi_discovery.py',
  'quiet.json',
  'wordfile.txt'
]

install_data(linux_client_gui_sources, install_dir: moduledir)
