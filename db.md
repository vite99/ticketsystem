erDiagram
    AUTH_USER ||--o{ TICKET : creates
    AUTH_USER ||--o{ TICKET : assigns_to
    AUTH_USER ||--o{ COMMENT : authors
    AUTH_USER ||--o{ ATTACHMENT : uploads
    AUTH_USER ||--o{ TICKETHISTORY : performs
    AUTH_USER ||--o{ USERPROFILE : has
    AUTH_USER ||--o{ USERPROFILE : approves

    TICKET ||--o{ COMMENT : has
    TICKET ||--o{ ATTACHMENT : contains
    TICKET ||--o{ TICKETHISTORY : records
    TICKET }o--|| PRIORITY : has
    TICKET }o--|| STATUS : has
    TICKET }o--|| WORKSTATION : located_at
    TICKET }o--o{ TAG : tagged_with

    COMMENT ||--o{ ATTACHMENT : contains

    USERPROFILE }o--|| WORKSTATION : assigned_to

    AUTH_USER {
        int id PK
        string username UK
        string email UK
        string first_name
        string last_name
        boolean is_staff
        boolean is_active
    }

    TICKET {
        int id PK
        string title
        text description
        int creator_id FK
        int assigned_to_id FK "nullable"
        int priority_id FK "nullable"
        int status_id FK "nullable"
        int workstation_id FK "nullable"
        string user_urgency
        string room "nullable"
        datetime created_at
        datetime updated_at
        datetime resolved_at "nullable"
        datetime closed_at "nullable"
        datetime due_date "nullable"
        float estimated_hours "nullable"
    }

    PRIORITY {
        int id PK
        string name UK
        string color "HEX"
    }

    STATUS {
        int id PK
        string name UK
        string color "HEX"
        boolean is_final
    }

    TAG {
        int id PK
        string name UK
        text description
        string color "HEX"
    }

    WORKSTATION {
        int id PK
        string room
        string number
        string location "nullable"
    }

    COMMENT {
        int id PK
        int ticket_id FK
        int author_id FK
        text content
        datetime created_at
        datetime updated_at
        boolean is_internal
    }

    ATTACHMENT {
        int id PK
        int ticket_id FK "nullable"
        int comment_id FK "nullable"
        string file
        int uploaded_by_id FK "nullable"
        datetime uploaded_at
        string description
    }

    TICKETHISTORY {
        int id PK
        int ticket_id FK
        int actor_id FK "nullable"
        string action
        text old_value
        text new_value
        datetime created_at
    }

    USERPROFILE {
        int id PK
        int user_id FK "OneToOne"
        int approved_by_id FK "nullable"
        int workstation_id FK "nullable"
        boolean is_approved
        datetime approved_at "nullable"
        string office_room
        string department
        string phone
        boolean notify_email
        string notify_email_address
        boolean notify_vk
        boolean notify_browser
        string vk_user_id
    }
