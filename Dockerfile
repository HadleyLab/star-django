FROM python:3.6.9-slim
# Install R and its meta package
RUN apt-get update && apt-get install -y --no-install-recommends \
     r-base-core r-base-dev \
     libpq-dev \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*
RUN bash -c "echo 'install.packages(\"meta\",repos=\"http://cran.rstudio.com/\")' | R --no-save"
# Install Python deps
RUN mkdir -p /app/user /app/logs
WORKDIR /app/user
RUN pip install --upgrade pip
COPY requirements.txt requirements-dev.txt /app/user/
RUN pip install -r requirements.txt -r requirements-dev.txt
# Add code
COPY . .
EXPOSE 8000
