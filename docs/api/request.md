::: pykour.Request
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
        # explicit members list so we can set order and include `__init__` easily
        members:
          - __init__
          - app
          - url
          - headers
          - get_header
          - method
          - version
          - query_string
          - body
          - json
