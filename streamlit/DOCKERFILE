# TODO: Add/Update your HW3.
# Use python:3.13-slim as a base image 
FROM python:3.13-slim

# Set /Day8 as a working directory in the container
WORKDIR /streamlit

# Copy everything in the working directory to /Day8 in the container
COPY * ./

# Install packages and libraries
RUN pip install -r requirements.txt

# expose port 8501
EXPOSE 8501

# run the hw4.py.
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]