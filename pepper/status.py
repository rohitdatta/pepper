NEW = 'NEW'
PENDING = 'PENDING'
WAITLISTED = 'WAITLISTED'
ACCEPTED = 'ACCEPTED'
REJECTED = 'REJECTED'
DECLINED = 'DECLINED'
SIGNING = 'SIGNING'
CONFIRMED = 'CONFIRMED'
LATE = 'LATE'   # Not applicable for regular method of acceptance. Must be accepted through puzzle challenge
ADMIN = 'ADMIN'


STATUS_LEVEL = {
    NEW: 0,
    PENDING: 1,
    WAITLISTED: 2,
    ACCEPTED: 3,
    REJECTED: 4,
    DECLINED: 5,
    SIGNING: 6,
    CONFIRMED: 7,
    LATE: 8,
    ADMIN: 999,
}
