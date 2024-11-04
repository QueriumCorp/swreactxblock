# delete anything in swpwrxblock/public except for README.md
find ../swpwrxblock/public/* ! -name 'README.md' -type f -exec rm -f {} +
