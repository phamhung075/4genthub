---
alwaysApply: true
description: Guide to writing clear, structured, and maintainable documentation in a technical project.
tags: [documentation, guide, structure, notes]
globs: path/to/concerned/files/**
---

## how-to-write-documentation.md

#documentation

This document explains **how to write correct and useful documentation** for a software or technical project. It serves as a reference for all contributors to ensure consistent quality across the `.md` files in the `ai_docs/` folder.

---

### Goals

- Define a clear structure for every documentation file.
    
- Ensure readability, maintainability, and practical value.
    
- Encourage documentation at the creation or modification of a component, module, or feature.
    

---

### Recommended Structure

Each document should follow this structure:

1. **YAML Front Matter**  
    Used for referencing, filtering, and applying automation rules:
    
    ```yaml
    ---
    alwaysApply: true
    description: Short description of the documentation topic.
    tags: [mainTag, secondaryTag]
    globs: path/to/concerned/files/**
    ---
    ```
    
2. **Title of the File**  
    Use a clear and concise title that reflects the content.
    
    ```markdown
    ## ExampleComponent Documentation
    ```
    
3. **Primary Tag as Heading**  
    This helps categorize the content visually and semantically.
    
    ```markdown
    #component
    ```
    
4. **Main Content**  
    Clearly explain:
    
    - The **objective** of the file or feature.
        
    - The **steps** to implement or use it.
        
    - Any **technical decisions** or alternatives considered.
        
    - Potential **limitations** or future improvements.
        
    
    ```markdown
    This component handles the display of user notifications and is used across multiple modules. It listens to the `NotificationService` and renders toast messages.
    ```
    
5. **Code Examples (if relevant)**  
    Include usage examples, configuration, and edge case handling.
    
    ```ts
    import { NotificationService } from '@shared/services';
    
    this.notificationService.show('Success message', 'success');
    ```
    
6. **Appendix (Optional)**  
    Additional notes, links, or specifications.
    
    ```markdown
    ---
    ### Appendix
    #notes
    
    - Refer to `NotificationModule` for setup instructions.
    - Design follows the accessibility guidelines WCAG 2.1.
    ```
    

---

### Full Example

````markdown
---
alwaysApply: true
description: Documentation for the user notification component and its usage.
tags: [component, ui]
globs: src/app/shared/components/notification/**
---

## NotificationComponent Documentation

#component

This component displays user-facing toast notifications using a service-based architecture. It supports various types like success, error, info, and warning.

---

### Usage

1. Import the `NotificationModule` in your feature module.
2. Inject the `NotificationService` in your component or service.
3. Trigger messages using `show()`.

```ts
this.notificationService.show('Update saved successfully', 'success');
````

---

### Appendix

#notes

- Automatically disappears after 5 seconds (configurable).
    
- Messages are keyboard-navigable and screen-reader accessible.