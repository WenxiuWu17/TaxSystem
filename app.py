from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tax_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # 用於 flash 訊息
db = SQLAlchemy(app)

# 公司資料模型
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    tax_id = db.Column(db.String(50), nullable=False)

# 員工資料模型
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    salary = db.Column(db.Integer, nullable=False)  
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    tax_amount = db.Column(db.Integer, nullable=True)  # 員工稅額
    taxable_income = db.Column(db.Integer, nullable=True)  # 員工應稅所得

    company = db.relationship('Company', backref=db.backref('employees', lazy=True))

# 初始化資料庫
with app.app_context():
    #db.drop_all()
    db.create_all()

# 首頁路由
@app.route('/')
def index():
    return render_template('index.html')

# 公司資料頁面
@app.route('/company', methods=['GET', 'POST'])
def company():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        tax_id = request.form['tax_id']
        
        # 檢查是否已有相同名稱的公司
        existing_company = Company.query.filter_by(name=name).first()
        if existing_company:
            flash('公司名稱已存在，無法新增！', 'error')
            return redirect(url_for('company'))  # 重定向回該頁面以顯示錯誤訊息

        # 如果公司名稱不重複，新增公司資料
        company = Company(name=name, address=address, phone=phone, tax_id=tax_id)
        db.session.add(company)
        db.session.commit()
        flash('公司資料已成功新增！', 'success')
    
    companies = Company.query.all()
    return render_template('company.html', companies=companies)

# 員工資料頁面
@app.route('/employee', methods=['GET', 'POST'])
def employee():
    if request.method == 'POST':
        name = request.form['name']
        gender = request.form['gender']
        salary = int(request.form['salary'])  # 確保薪資為整數
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        company_id = request.form['company_id']
        
        employee = Employee(name=name, gender=gender, salary=salary, address=address, phone=phone, email=email, company_id=company_id)
        db.session.add(employee)
        db.session.commit()
        flash('員工資料已成功新增！', 'success')
    
    companies = Company.query.all()
    employees = Employee.query.all()
    return render_template('employee.html', companies=companies, employees=employees)

# 稅額試算頁面
@app.route('/tax_calculation', methods=['GET', 'POST'])
def tax_calculation():
    tax_info = None
    companies = Company.query.all()
    selected_company_id = request.form.get('company_id')
    
    if selected_company_id:
        employees = Employee.query.filter_by(company_id=selected_company_id).all()
    else:
        employees = []

    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_id = request.form.get('employee_id')
        salary = 0
        employee_name = ''

        if employee_id:
            employee = Employee.query.get(employee_id)
            salary = employee.salary
            employee_name = employee.name

        num_under_70 = int(request.form.get('num_under_70'))
        num_over_70 = int(request.form.get('num_over_70'))
        num_disability = int(request.form.get('num_disability'))
        num_education = int(request.form.get('num_education'))
        num_child = int(request.form.get('num_child'))
        num_care = int(request.form.get('num_care'))

        # 檢查扣除人數是否超過免稅額人數
        total_exemption = num_under_70 + num_over_70
        total_deductions = num_disability + num_education + num_child + num_care

        if total_deductions > total_exemption:
            # 如果扣除額人數超過免稅額人數，返回錯誤訊息
            return render_template(
                'tax_calculation.html',
                companies=companies,
                employees=employees,
                tax_info=None,
                selected_company_id=selected_company_id,
                error_message="身心障礙扣除、教育學費扣除、幼兒學前扣除、長期照護扣除人數的總和不能超過免稅額人數的總和。"
            )

        salary_income = salary - 207000
        exemption_amount = (num_under_70 * 92000) + (num_over_70 * 145500)
        standard_deduction = 124000
        disability_deduction = num_disability * 207000
        education_deduction = num_education * 25000
        child_deduction = num_child * 120000
        care_deduction = num_care * 120000

        total_deductions = (
            standard_deduction + disability_deduction +
            education_deduction + child_deduction + care_deduction
        )

        taxable_income = salary_income - exemption_amount - total_deductions
        taxable_income = max(taxable_income, 0)

        tax_amount = 0
        if taxable_income <= 540000:
            tax_amount = taxable_income * 0.05
        elif taxable_income <= 1210000:
            tax_amount = 540000 * 0.05 + (taxable_income - 540000) * 0.12
        elif taxable_income <= 2420000:
            tax_amount = (
                540000 * 0.05 + (1210000 - 540000) * 0.12 +
                (taxable_income - 1210000) * 0.2
            )
        else:
            tax_amount = (
                540000 * 0.05 + (1210000 - 540000) * 0.12 +
                (2420000 - 1210000) * 0.2 + (taxable_income - 2420000) * 0.3
            )

        tax_amount = round(tax_amount, 0)

        if employee:
            employee.taxable_income = taxable_income
            employee.tax_amount = tax_amount
            db.session.commit()

        tax_info = {
            'employee_name': employee_name,
            'salary_income': salary_income,
            'exemption_amount': exemption_amount,
            'total_deductions': total_deductions,
            'taxable_income': taxable_income,
            'tax_amount': tax_amount,
        }

    return render_template(
        'tax_calculation.html',
        companies=companies,
        employees=employees,
        tax_info=tax_info,
        selected_company_id=selected_company_id,
        error_message=None
    )


# 新增路由處理員工資料的 AJAX 請求
@app.route('/get_employees/<company_id>', methods=['GET'])
def get_employees(company_id):
    employees = Employee.query.filter_by(company_id=company_id).all()
    employee_list = [{"id": e.id, "name": e.name} for e in employees]
    return jsonify(employee_list)



# 稅務統計頁面
@app.route('/tax_statistic', methods=['GET', 'POST'])
def tax_statistic():
    companies = Company.query.all()
    selected_company_id = request.form.get('company_id')
    selected_company = None
    tax_statistics = []
    total_tax = 0

    if selected_company_id:
        selected_company = Company.query.get(selected_company_id)
        # 從資料庫中取得該公司員工的應稅所得和稅額
        for employee in selected_company.employees:
            tax_statistics.append({
                'employee_name': employee.name,
                'taxable_income': employee.taxable_income,
                'tax_amount': employee.tax_amount if employee.tax_amount else 0
            })
            total_tax += employee.tax_amount if employee.tax_amount else 0

    return render_template(
        'tax_statistics.html',
        companies=companies,
        selected_company=selected_company,
        total_tax=total_tax if selected_company else 0,
        tax_statistics=tax_statistics
    )


if __name__ == '__main__':
    app.run(debug=True)
