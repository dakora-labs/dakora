"""Example: Delete a template using the Dakora Python SDK

This example demonstrates how to delete a template using the Dakora client SDK.
"""

import asyncio
from dakora_client import DakoraClient


async def main():
    # Initialize client
    client = DakoraClient(base_url="http://localhost:54321")
    
    try:
        # List all templates
        print("Current templates:")
        templates = await client.prompts.list()
        for template_id in templates:
            print(f"  - {template_id}")
        
        # Delete a template
        template_to_delete = "example-template"
        print(f"\nDeleting template: {template_to_delete}")
        
        try:
            await client.prompts.delete(template_to_delete)
            print(f"✓ Template '{template_to_delete}' deleted successfully")
        except Exception as e:
            print(f"✗ Failed to delete template: {e}")
        
        # List templates again to confirm deletion
        print("\nTemplates after deletion:")
        templates = await client.prompts.list()
        for template_id in templates:
            print(f"  - {template_id}")
            
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
