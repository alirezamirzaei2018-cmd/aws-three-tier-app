# ☁️ AWS Three-Tier Web Application Deployment (S3 + EC2 + RDS)

This project demonstrates the **end-to-end deployment of a three-tier web application** on AWS — integrating a **frontend hosted on S3**, a **Flask backend on EC2 behind an Application Load Balancer (ALB)**, and a **MySQL database on RDS**.  

This was a complete hands-on project built and tested by **Alireza Mirzaei**, as part of personal AWS learning and practical architecture design experience.

---

## 🧩 1. Project Overview

The **Three-Tier Architecture** is a common cloud design pattern consisting of:

| Tier | Component | Description |
|------|------------|-------------|
| **Presentation Layer** | AWS S3 (Static Website) | User-facing HTML/JavaScript frontend |
| **Application Layer** | EC2 Instances + Flask App | Logic and API hosted privately behind an ALB |
| **Database Layer** | Amazon RDS (MySQL) | Secure and managed data storage |

This architecture ensures **scalability**, **fault tolerance**, and **security isolation** between tiers.

---

## 🌐 2. VPC and Network Design

### 🧱 VPC Setup
| Setting | Value |
|----------|--------|
| VPC Name | three-tier-vpc |
| CIDR Block | 10.0.0.0/16 |

<p align="center">
  <img src="screenshots/1-VPC-Subnet/01-VPC-creation1.png" alt="AWS 3-Tier Architecture" width="700"/>
</p>

### 🌍 Subnets
| Subnet Name | Type | CIDR | Availability Zone |
|--------------|------|------|--------------------|
| Public-Subnet-1 | Public | 10.0.0.0/24 | ca-central-1a |
| Public-Subnet-2 | Public | 10.0.1.0/24 | ca-central-1b |
| Private-Subnet-1 | Private | 10.0.2.0/24 | ca-central-1a |
| Private-Subnet-2 | Private | 10.0.3.0/24 | ca-central-1b |

### 🔌 Internet Gateway and NAT Gateway
- Created **Internet Gateway (IGW)** and attached to VPC.  
- Created **NAT Gateway** in Public Subnet 1 with an Elastic IP.  
- Private subnets route outbound internet access through NAT Gateway.  

### 🛣️ Route Tables
| Route Table | Destination | Target |
|--------------|-------------|---------|
| Public | 0.0.0.0/0 | Internet Gateway |
| Private | 0.0.0.0/0 | NAT Gateway |

---

## 🔐 3. Bastion Host (Public Subnet)

The **Bastion Host** acts as a secure jump server to SSH into private EC2 instances.  
Since the private EC2s have no public IP, you must connect through the Bastion, which resides in the public subnet.

| Setting | Value |
|----------|--------|
| **AMI** | Amazon Linux 2 |
| **Type** | t2.micro |
| **Subnet** | Public |
| **Security Group Rule** | Allow inbound SSH (port 22) only from your own IP |

---

### ⚙️ Step-by-Step Configuration

#### 🟢 Step 1 — Connect to Bastion Host
From your local system, SSH into the Bastion using the downloaded key pair:

```bash
ssh -i three-tier-key.pem ec2-user@<BASTION_PUBLIC_IP>
```

---

#### 🟡 Step 2 — Copy the Private Key to Bastion
You’ll need the same private key (`three-tier-key.pem`) inside the Bastion host to connect to private EC2 instances.

From your **local machine**, use SCP to copy the key file into the Bastion:

```bash
scp -i three-tier-key.pem three-tier-key.pem ec2-user@<BASTION_PUBLIC_IP>:/home/ec2-user/
```

Once inside the Bastion, set the correct permissions:

```bash
chmod 400 three-tier-key.pem
```

---

#### 🔵 Step 3 — Connect from Bastion to Private EC2
Now you can SSH from the Bastion to your private EC2 instances using the same key:

```bash
ssh -i three-tier-key.pem ec2-user@<PRIVATE_EC2_IP>
```

Example:
```bash
ssh -i three-tier-key.pem ec2-user@10.0.2.107
ssh -i three-tier-key.pem ec2-user@10.0.3.107
```

---

## 🗄️ 4. RDS (Database Layer)

### Database Configuration
| Parameter | Value |
|------------|--------|
| Engine | MySQL |
| DB Instance Class | db.t3.micro |
| Multi-AZ | Disabled |
| Public Access | No |
| Subnet Group | Private Subnets |
| Security Group | Allow port 3306 from EC2 SG only |

### Create Schema and Sample Data
From Bastion → EC2 → connect to RDS:
```bash
sudo yum install mariadb105 -y
mysql -h three-tier-db.xxxxxx.ca-central-1.rds.amazonaws.com -u admin -p
```

Inside MySQL:
```sql
CREATE DATABASE company;
USE company;
CREATE TABLE employees (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50));
INSERT INTO employees (name) VALUES ('Alireza'), ('Sara'), ('John');
```

---

## 🐍 5. Flask Backend (Application Layer)

### EC2 Configuration
| Parameter | Value |
|------------|--------|
| AMI | Amazon Linux 2 |
| Instance Type | t2.micro |
| Subnet | Private |
| SG Rule | Allow 5000 from ALB, 22 from Bastion |

SSH to each EC2 through Bastion, then install Python and Flask:

```bash
sudo yum update -y
sudo yum install python3 -y
python3 -m pip install flask pymysql
```

Create the app file:
```bash
nano /home/ec2-user/app.py
```

Paste the following code:
```python
from flask import Flask, jsonify
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)

# Connect to RDS
db = pymysql.connect(
    host='three-tier-db.xxxxxx.ca-central-1.rds.amazonaws.com',
    user='admin',
    password='YourPassword',
    database='company'
)

@app.route('/')
def home():
    return "<h2>Hello from Flask App on EC2 via ALB!</h2>"

@app.route('/employees')
def employees():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM employees;")
        rows = cursor.fetchall()
        data = [{"id": r[0], "name": r[1]} for r in rows]
        return jsonify(data)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Run Flask as a background service:
```bash
nohup python3 /home/ec2-user/app.py &
```

Test internally:
```bash
curl http://localhost:5000
curl http://localhost:5000/employees
```

---

## ⚖️ 6. Application Load Balancer (ALB)

| Setting | Value |
|----------|--------|
| Type | Application Load Balancer |
| Scheme | Internet-facing |
| Listener | HTTP : 80 |
| Target Group | EC2 Instances (port 5000) |
| Health Check | Path `/` |

Add both EC2 instances as targets and wait until health status = “healthy”.

Test:
```
http://<ALB-DNS>
```

---

## 🪣 7. Frontend (S3 Static Website)

### Step 1 — Create S3 Bucket
| Setting | Value |
|----------|--------|
| Name | three-tier-frontend-alireza |
| Public Access | Disabled (uncheck “Block all public access”) |
| Static Website Hosting | Enabled |
| Index Document | index.html |

### Step 2 — Bucket Policy
```json
{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Principal":"*",
    "Action":["s3:GetObject"],
    "Resource":["arn:aws:s3:::three-tier-frontend/*"]
  }]
}
```

### Step 3 — Upload index.html
```html
<!DOCTYPE html>
<html>
<head>
  <title>My AWS 3-Tier App</title>
</head>
<body>
  <h1>My AWS 3-Tier App</h1>
  <p>Frontend hosted on S3 + Flask + RDS</p>
  <button onclick="loadEmployees()">Load Employees</button>
  <ul id="employees"></ul>

  <script>
    async function loadEmployees() {
      const response = await fetch('http://<ALB-DNS>/employees');
      const data = await response.json();
      const list = document.getElementById('employees');
      list.innerHTML = '';
      data.forEach(emp => {
        const li = document.createElement('li');
        li.textContent = `${emp.id}: ${emp.name}`;
        list.appendChild(li);
      });
    }
  </script>
</body>
</html>
```

### Step 4 — Test Frontend
Visit:
```
http://three-tier-frontend-alireza.s3-website.ca-central-1.amazonaws.com
```
✅ The app displays a button “Load Employees” and retrieves data via ALB → EC2 → RDS.

---

## 📊 8. Final Architecture Diagram

```
          +---------------------+
          |      User (Browser) |
          +---------------------+
                     |
                     v
          +---------------------+
          | S3 Static Website   |
          +---------------------+
                     |
                     v
          +---------------------+
          | Application Load Balancer |
          +---------------------+
                     |
           ┌─────────┴─────────┐
           ▼                   ▼
   +----------------+   +----------------+
   | EC2 App Server |   | EC2 App Server |
   +----------------+   +----------------+
           |                   |
           └──────────┬────────┘
                      ▼
               +--------------+
               |   RDS MySQL  |
               +--------------+

         Bastion Host → SSH to Private EC2
```

---


## 🧠 9. AWS Services Summary

| Service | Purpose |
|----------|----------|
| **VPC** | Isolated network for the app |
| **Subnets** | Logical separation of layers |
| **Internet Gateway** | Internet access for public subnets |
| **NAT Gateway** | Outbound access for private subnets |
| **EC2** | Hosts Flask application |
| **RDS MySQL** | Stores application data |
| **ALB** | Balances traffic across EC2 instances |
| **S3** | Hosts static frontend |
| **Bastion Host** | Secure SSH to private EC2 |
| **Security Groups** | Access control between layers |

---

## 🧰 10. Tools and Skills Demonstrated

- **AWS Services:** VPC, EC2, RDS, S3, ALB, IAM  
- **Networking:** CIDR design, routing, NAT/IGW, SG rules  
- **Programming:** Python Flask, MySQL, HTML, JS  
- **DevOps Skills:** SSH, nohup, Linux, GitHub versioning  
- **Architecture Design:** Secure and scalable 3-tier setup  

---

## 👨‍💻 11. Author

**Alireza Mirzaei**  
📍 Toronto, Canada    
📧 alirezamirzaei2018@gmail.com
🌐 https://www.linkedin.com/in/alireza-mirzaei-b2a5a31a4/
🧰 [GitHub Repository](https://github.com/alirezamirzaei2018-cmd/aws-three-tier-app)

---

## 🧾 License
This project is for educational and demonstration purposes only.  
© 2025 Alireza Mirzaei. All rights reserved.
