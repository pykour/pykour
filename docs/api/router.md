Pydantic models are simply classes which inherit from `BaseModel` and define fields as annotated attributes.

::: pykour.Router
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
        # explicit members list so we can set order and include `__init__` easily
        members:
          - __init__
          - get
          - post
          - put
          - delete
          - patch
          - options
          - head
          - route
          - add_router
          - add_route
          - get_route
          - exists