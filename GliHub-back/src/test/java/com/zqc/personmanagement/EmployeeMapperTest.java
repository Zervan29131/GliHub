package com.zqc.personmanagement;

import com.zqc.personmanagement.mapper.DepartmentMapper;
import com.zqc.personmanagement.mapper.EmployeeMapper;
import com.zqc.personmanagement.pojo.Employee;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

@SpringBootTest
public class EmployeeMapperTest {

    @Autowired
    EmployeeMapper employeeMapper;

    @Autowired
    DepartmentMapper departmentMapper;

    @Test
    void testQueryEmployeeList() {
        List<Employee> employeeList = employeeMapper.queryEmployeeList();
        System.out.println(employeeList);
    }

    @Test
    void testQueryEmployeeById() {
        Employee employee = employeeMapper.queryEmployeeById(1001);
        System.out.println(employee);
    }

    @Test
    void testAddEmployee() {
        int x = employeeMapper.addEmployee(new Employee(null, "员工x", "xxx@qq.com", 1, departmentMapper.queryDepartmentById(101)));
        System.out.println(x);
    }

    @Test
    void testUpdateEmployee() {
        int y = employeeMapper.updateEmployee(new Employee(1007, "员工y", "yyy@qq.com", 1, departmentMapper.queryDepartmentById(101)));
        System.out.println(y);
    }

    @Test
    void testDeleteEmployeeById() {
        int i = employeeMapper.deleteEmployeeById(1006);
        System.out.println(i);
    }
}
