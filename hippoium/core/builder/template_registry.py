# hippoium/core/builder/template_registry.py

import os
import yaml
import string
from typing import Dict, List, Optional

try:
    from hippoium.ports.mcp import PromptTemplate
except ImportError:
    # Fallback: define a simple PromptTemplate if not available
    class PromptTemplate:
        def __init__(self, content: str, name: Optional[str] = None, description: Optional[str] = None):
            self.content = content
            self.name = name
            self.description = description

class TemplateRegistry:
    """
    Manages prompt templates. Supports loading templates from YAML files and dynamic registration.
    Can query templates and their slots, and perform hot-reloading of templates from disk.
    """
    def __init__(self) -> None:
        self.templates: Dict[str, PromptTemplate] = {}
        self.template_slots: Dict[str, List[str]] = {}
        self._source_path: Optional[str] = None
        self._file_templates: set = set()  # track templates loaded from files (for reload)

    def load_from_path(self, path: str) -> None:
        """
        Load prompt templates from the given path. If `path` is a directory, all .yaml/.yml files inside are loaded.
        If `path` is a file, that YAML file is loaded.
        """
        self._source_path = path
        loaded_file_templates: set = set()
        if os.path.isdir(path):
            # Load all YAML files in directory
            for fname in os.listdir(path):
                if fname.lower().endswith((".yaml", ".yml")):
                    file_path = os.path.join(path, fname)
                    self._load_yaml_file(file_path, loaded_file_templates)
        elif os.path.isfile(path):
            # Load a single YAML file
            self._load_yaml_file(path, loaded_file_templates)
        else:
            raise FileNotFoundError(f"Template path {path} does not exist.")
        # Remove any templates that were previously loaded from files but are no longer present
        for name in list(self._file_templates):
            if name not in loaded_file_templates:
                self.templates.pop(name, None)
                self.template_slots.pop(name, None)
        # Update the set of file-loaded templates
        self._file_templates = loaded_file_templates

    def _load_yaml_file(self, file_path: str, loaded_names: set) -> None:
        """Helper to load templates from a single YAML file and update registry."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if data is None:
            return
        # Determine structure of YAML: could be a list of templates or a dict
        templates_data = []
        if isinstance(data, list):
            templates_data = data
        elif isinstance(data, dict):
            if "templates" in data and isinstance(data["templates"], list):
                templates_data = data["templates"]
            else:
                # Treat each key as template name and value as content or template info
                for name, content in data.items():
                    if isinstance(content, dict):
                        entry = {"name": name}
                        entry.update(content)
                        templates_data.append(entry)
                    else:
                        templates_data.append({"name": name, "content": content})
        else:
            return  # unsupported format
        for entry in templates_data:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            content = entry.get("content")
            if not name or content is None:
                continue  # skip invalid entries
            description = entry.get("description")
            # Create PromptTemplate and store it
            template = PromptTemplate(content=content, name=name, description=description)
            self.templates[name] = template
            # Determine slots (placeholders) in the content
            if entry.get("slots") is not None:
                slots = list(entry["slots"])
            else:
                slots = self._extract_slots_from_content(content)
            self.template_slots[name] = slots
            loaded_names.add(name)

    def _extract_slots_from_content(self, content: str) -> List[str]:
        """Extract placeholder slot names from a template content string (e.g., {name} in the text)."""
        slots: List[str] = []
        try:
            formatter = string.Formatter()
            for _, field_name, _, _ in formatter.parse(content):
                if field_name:
                    slots.append(field_name)
        except Exception:
            # Fallback: regex extraction if formatter fails
            import re
            slots = re.findall(r"\{(\w+)\}", content)
        # Remove duplicates while preserving order
        seen = set()
        unique_slots: List[str] = []
        for slot in slots:
            if slot not in seen:
                seen.add(slot)
                unique_slots.append(slot)
        return unique_slots

    def register_template(self, name: str, content: str, description: Optional[str] = None) -> None:
        """
        Dynamically register a new template or update an existing one.
        """
        template = PromptTemplate(content=content, name=name, description=description)
        self.templates[name] = template
        # Compute slots for the template content
        slots = self._extract_slots_from_content(content)
        self.template_slots[name] = slots
        # Note: dynamic templates are not added to _file_templates, so they persist through reloads

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Retrieve a template by name."""
        return self.templates.get(name)

    def get_template_slots(self, name: str) -> List[str]:
        """Get the list of slot placeholder names for a given template."""
        return self.template_slots.get(name, [])

    def list_templates(self) -> List[str]:
        """List all template names available in the registry."""
        return list(self.templates.keys())

    def hot_reload(self) -> None:
        """
        Reload templates from the original source path (if set via load_from_path).
        Updates templates that changed on disk and retains dynamically registered templates.
        """
        if not self._source_path:
            return
        # Reload from the stored source path
        self.load_from_path(self._source_path)