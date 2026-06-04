import streamlit_authenticator as stauth

# Use the static hash method directly
hashed_pw = stauth.Hasher.hash('1234')
print(hashed_pw)