#!/bin/bash
# Mount Windows Zotero Share - Pre-configured
# This script attempts to mount with different credential combinations

echo "========================================"
echo "Mount Windows Zotero Share"
echo "========================================"
echo ""

# Configuration
WINDOWS_HOST="DESKTOP-51JB4Q"
SHARE_NAME="Zotero"
WINDOWS_USER="Tom Ochs i9"
MOUNT_POINT="$HOME/windows_zotero"

# Create mount point if it doesn't exist
mkdir -p "$MOUNT_POINT"

# Attempt 1: Without password (blank password) - MOST COMMON FOR WINDOWS SHARES
echo "Attempt 1: Mounting with username and blank password..."
echo ""

sudo mount -t cifs "//$WINDOWS_HOST/$SHARE_NAME" "$MOUNT_POINT" \
    -o username="$WINDOWS_USER",password="",uid=$(id -u),gid=$(id -g),ro 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Mount successful with blank password"
    echo ""
    echo "Zotero data is now accessible at: $MOUNT_POINT"
    echo ""
    echo "Checking for Zotero database..."

    if [ -f "$MOUNT_POINT/zotero.sqlite" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite"
        SIZE=$(ls -lh "$MOUNT_POINT/zotero.sqlite" | awk '{print $5}')
        echo "   Size: $SIZE"
    fi

    if [ -f "$MOUNT_POINT/zotero.sqlite.bak" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite.bak"
    fi

    if [ -d "$MOUNT_POINT/storage" ]; then
        ITEM_COUNT=$(find "$MOUNT_POINT/storage" -maxdepth 1 -type d 2>/dev/null | wc -l)
        echo "✅ Found storage directory with $ITEM_COUNT items"
    fi

    echo ""
    echo "To unmount later:"
    echo "  sudo umount $MOUNT_POINT"
    exit 0
fi

# Attempt 2: Guest access (no credentials)
echo "⚠️  First attempt failed. Trying guest access..."
echo ""

sudo mount -t cifs "//$WINDOWS_HOST/$SHARE_NAME" "$MOUNT_POINT" \
    -o guest,uid=$(id -u),gid=$(id -g),ro 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Mount successful with guest access"
    echo ""
    echo "Zotero data is now accessible at: $MOUNT_POINT"
    echo ""
    echo "Checking for Zotero database..."

    if [ -f "$MOUNT_POINT/zotero.sqlite" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite"
        SIZE=$(ls -lh "$MOUNT_POINT/zotero.sqlite" | awk '{print $5}')
        echo "   Size: $SIZE"
    fi

    if [ -f "$MOUNT_POINT/zotero.sqlite.bak" ]; then
        echo "✅ Found: $MOUNT_POINT/zotero.sqlite.bak"
    fi

    if [ -d "$MOUNT_POINT/storage" ]; then
        ITEM_COUNT=$(find "$MOUNT_POINT/storage" -maxdepth 1 -type d 2>/dev/null | wc -l)
        echo "✅ Found storage directory with $ITEM_COUNT items"
    fi

    echo ""
    echo "To unmount later:"
    echo "  sudo umount $MOUNT_POINT"
    exit 0
fi

# All attempts failed
echo "❌ All mount attempts failed. Diagnostics:"
echo ""
echo "Testing network connectivity..."
ping -c 2 $WINDOWS_HOST 2>&1 | grep -E "bytes from|Destination Host Unreachable|100% packet loss"
echo ""
echo "Please verify:"
echo "  1. Windows computer DESKTOP-51JB4Q is on and connected to network"
echo "  2. Share 'Zotero' exists and is accessible on Windows"
echo "  3. Windows username is 'Tom Ochs i9'"
echo "  4. Network discovery and file sharing are enabled on Windows"
echo ""
echo "On Windows, check:"
echo "  - Control Panel → Network and Sharing Center → Advanced sharing settings"
echo "  - Make sure 'Turn on network discovery' and 'Turn on file and printer sharing' are enabled"
echo ""
echo "If you have the correct password, you can mount manually with:"
echo "  sudo mount -t cifs '//DESKTOP-51JB4Q/Zotero' '$MOUNT_POINT' -o username='Tom Ochs i9',password='YOUR_PASSWORD',uid=\$(id -u),gid=\$(id -g),ro"
exit 1
