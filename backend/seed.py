from database import engine, Base
from sqlalchemy.orm import Session
from models import EmailRequest

Base.metadata.create_all(bind=engine)

sample_requests = [
    {
        "client": "ABC Technologies",
        "email": "contact@abc.com",
        "project": "Website Development",
        "description": "We need a professional business website.",
        "status": "Pending"
    },
    {
        "client": "XYZ Solutions",
        "email": "info@xyz.com",
        "project": "Mobile App Development",
        "description": "We need an Android application.",
        "status": "Under Review"
    },
    {
        "client": "Global Enterprises",
        "email": "hello@global.com",
        "project": "Software Development",
        "description": "We need custom business management software.",
        "status": "Approved"
    }
]

with Session(engine) as session:
    if session.query(EmailRequest).count() == 0:
        for request in sample_requests:
            session.add(EmailRequest(**request))

        session.commit()
        print("3 sample requests saved successfully!")
    else:
        print("Requests already exist. No duplicate records added.")