#!/bin/bash
# Fix YAML config file encoding and validate

echo "=========================================="
echo "YAML Config Fixer"
echo "=========================================="
echo ""

# Backup original
if [ ! -f config/config.yaml.backup ]; then
    cp config/config.yaml config/config.yaml.backup
    echo "✓ Created backup: config/config.yaml.backup"
fi

# Test YAML validity
echo "Testing YAML validity..."
python3 -c "
import yaml
import sys

try:
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print('✓ YAML is valid!')
    sys.exit(0)
except yaml.YAMLError as e:
    print(f'✗ YAML Error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "YAML is valid! No fix needed."
    exit 0
fi

echo ""
echo "YAML has errors. Attempting to fix..."
echo ""

# Try to fix by reading and rewriting (removes BOM, normalizes line endings)
python3 << 'PYTHON_SCRIPT'
import yaml
import sys

try:
    # Read with explicit UTF-8 encoding
    with open('config/config.yaml', 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Try to parse
    try:
        data = yaml.safe_load(content)
        print("✓ YAML parsed successfully after encoding fix")
    except yaml.YAMLError as e:
        print(f"✗ Still has YAML errors: {e}")
        print("\nTrying to fix common issues...")
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            print("  - Removed BOM")
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        print("  - Normalized line endings")
        
        # Try parsing again
        try:
            data = yaml.safe_load(content)
            print("✓ YAML fixed! Writing corrected file...")
            
            # Write back with proper encoding
            with open('config/config.yaml', 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            print("✓ File rewritten with proper encoding")
        except yaml.YAMLError as e2:
            print(f"✗ Could not fix YAML: {e2}")
            print("\nPlease check the file manually or restore from backup:")
            print("  cp config/config.yaml.backup config/config.yaml")
            sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "YAML fixed! Restarting dashboard..."
    echo "=========================================="
    docker compose restart dashboard
    sleep 5
    echo ""
    echo "Checking logs..."
    docker compose logs dashboard | grep -i "yaml\|error\|database" | tail -10
else
    echo ""
    echo "=========================================="
    echo "Could not auto-fix. Manual steps:"
    echo "=========================================="
    echo "1. Check file encoding: file config/config.yaml"
    echo "2. Convert to UTF-8: iconv -f UTF-8 -t UTF-8 config/config.yaml > config/config.yaml.new && mv config/config.yaml.new config/config.yaml"
    echo "3. Check line endings: dos2unix config/config.yaml (if dos2unix is installed)"
    echo "4. Or restore backup: cp config/config.yaml.backup config/config.yaml"
fi

