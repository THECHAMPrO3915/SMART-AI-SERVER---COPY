import streamlit_authenticator as stauth

# Use the static hash method directly
hashed_pw = stauth.Hasher.hash('123456')
print(hashed_pw)
