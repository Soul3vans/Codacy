.logout-form {
    margin: 0;
    padding: 0;
}

.logout-btn {
    transition: background-color 0.2s ease;
}

.logout-btn:hover {
    background-color: #f8f9fa !important;
}

.logout-btn:focus {
    outline: 2px solid #007bff;
    outline-offset: 2px;
}

/* Protección visual contra clickjacking */
.navbar {
    position: relative;
    z-index: 1000;
}