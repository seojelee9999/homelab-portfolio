#!/usr/bin/with-contenv bash
set -euo pipefail
# LSIO executes custom-cont-init.d after its BookStack migrations, before services.
# Probe gating remains closed if migration/bootstrap fails, even if s6 continues.
rm -f /run/portfolio-ready
s6-setuidgid abc php /portfolio-bootstrap/initialize.php
s6-setuidgid abc php /portfolio-bootstrap/configure.php
s6-setuidgid abc php /portfolio-bootstrap/authoring.php
touch /run/portfolio-ready
