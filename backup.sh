#!/bin/bash
tar -czvf backups/financiera_backup_$(date +%Y%m%d_%H%M%S).tar.gz financiera_data.db logs/
