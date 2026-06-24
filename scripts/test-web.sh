#!/bin/bash

cd "$(dirname "$0")/../web" || exit 1
npm run build && npm run test