package com.zqc.personmanagement.mapper;

import com.zqc.personmanagement.pojo.Employee;
import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Mapper
@Repository
public interface EmployeeMapper {
    List<Employee> queryEmployeeList();
    Employee queryEmployeeById(int id);
    int addEmployee(Employee Employee);
    int updateEmployee(Employee Employee);
    int deleteEmployeeById(int id);
}
