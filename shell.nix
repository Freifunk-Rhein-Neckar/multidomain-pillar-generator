with import <nixpkgs> {};
(python3.withPackages (ps: [ps.pyyaml ps.jinja2])).env
