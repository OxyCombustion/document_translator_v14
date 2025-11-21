#!/bin/bash
# Mount Windows Zotero Share
# Helper script to connect to Windows 11 desktop's Zotero database

echo "========================================"
echo "Mount Windows Zotero Share"
echo "========================================"
echo ""

# Configuration (you'll need to provide these)
read -p "Windows computer name or IP: " WINDOWS_HOST
read -p "Windows username: " WINDOWS_USER
read -sp "Windows password: " WINDOWS_PASS
echo ""
read -p "Zotero share path (e.g., Zotero or Users/YourName/Zotero): " SHARE_PATH

# Mount point
MOUNT_POINT="$HOME/windows_zotero"

# Create mount point if it doesn't exist
mkdir -p "$MOUNT_POINT"

echo ""
echo "Mounting //$WINDOWS_HOST/$SHARE_PATH to $MOUNT_POINT..."

# Mount the share
sudo mount -t cifs "//$WINDOWS_HOST/$SHARE_PATH" "$MOUNT_POINT" \
    -o username="$WINDOWS_USER",password="$WINDOWS_PASS",uid=$(id -u),gid=$(id -g),ro

if [ $? -eq 0 ]; then
    echo "✅ Mount successful!"
    echo ""
    echo "Zotero data is now accessible at: $MOUNT_POINT"
    echo ""
    echo "Checking for Zotero database..."

    if [ -f "$MOUNT_POINT/zotero.sqlite" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite"
    fi

    if [ -f "$MOUNT_POINT/zotero.sqlite.bak" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite.bak"
    fi

    if [ -d "$MOUNT_POINT/storage" ]; then
        ITEM_COUNT=$(find "$MOUNT_POINT/storage" -maxdepth 1 -type d | wc -l)
        echo "✅ Found storage directory with $ITEM_COUNT items"
    fi

    echo ""
    echo "To use with Python:"
    echo "  zotero_data_dir = Path('$MOUNT_POINT')"
    echo ""
    echo "To unmount later:"
    echo "  sudo umount $MOUNT_POINT"
else
    echo "❌ Mount failed. Please check:"
    echo "  1. Windows computer is accessible on network"
    echo "  2. Share is configured correctly"
    echo "  3. Credentials are correct"
fi
