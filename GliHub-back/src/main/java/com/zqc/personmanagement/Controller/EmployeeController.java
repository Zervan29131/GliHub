package com.zqc.personmanagement.Controller;

import com.zqc.personmanagement.mapper.DepartmentMapper;
import com.zqc.personmanagement.mapper.EmployeeMapper;
import com.zqc.personmanagement.pojo.Department;
import com.zqc.personmanagement.pojo.Employee;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.Collection;

@Controller
public class EmployeeController {
    @Autowired
    EmployeeMapper employeeMapper;

    @Autowired
    DepartmentMapper departmentMapper;

    @RequestMapping("/emps")
    public String List(Model model) {
        Collection<Employee> employees = employeeMapper.queryEmployeeList();
        model.addAttribute("emps", employees);
        return "emp/list";
    }

    @GetMapping("/emp")
    public String toAddpage(Model model) {
        // 查出所有部门的信息
        Collection<Department> departments = departmentMapper.queryDepartmentList();
        model.addAttribute("departments", departments);
        return "emp/add";
    }

    @PostMapping("/emp")
    public String addEmp(Employee employee) {
        // 添加操作
        employeeMapper.addEmployee(employee);  // 调用底层业务保存员工
        return "redirect:/emps";
    }

    // 员工修改页面
    @GetMapping("/emp/{id}")
    public String toUpdateEmp(@PathVariable("id") Integer id, Model model) {
        // 查出原来的数据
        Employee employee = employeeMapper.queryEmployeeById(id);
        model.addAttribute("emp", employee);

        // 查出所有部门的信息
        Collection<Department> departments = departmentMapper.queryDepartmentList();
        model.addAttribute("departments", departments);
        return "emp/update";
    }

    @PostMapping("/updateEmp")
    public String updateEmp(Employee employee) {
        employeeMapper.updateEmployee(employee);
        return "redirect:/emps";
    }

    @GetMapping("/removeEmp/{id}")
    public String removeEmp(@PathVariable("id") Integer id) {
        employeeMapper.deleteEmployeeById(id);
        return "redirect:/emps";
    }

}
